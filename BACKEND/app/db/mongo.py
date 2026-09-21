from typing import Any, AsyncIterator, Iterator, Sequence
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
)
from langchain_core.runnables import RunnableConfig
from app.config import Settings, settings

client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=500)
_mongo_available: bool | None = None

async def _check_mongo_connection() -> bool:
    global _mongo_available
    if _mongo_available is not None:
        return _mongo_available
    try:
        await client.admin.command("ping", maxTimeMS=200)
        _mongo_available = True
    except Exception:
        _mongo_available = False
    return _mongo_available

def get_client() -> AsyncIOMotorClient:
    return client

def get_database() -> AsyncIOMotorDatabase:
    return client[settings.MONGODB_DB_NAME]

async def close_client() -> None:
    client.close()

class AsyncMongoDBSaver(BaseCheckpointSaver):
    def __init__(self, database: AsyncIOMotorDatabase, serde: Any = None):
        super().__init__(serde=serde)
        self.database = database
        self.checkpoints = database["checkpoints"]
        self.writes = database["checkpoint_writes"]
        self._mem_checkpoints: dict[str, dict[str, Any]] = {}
        self._mem_writes: list[dict[str, Any]] = []

    def _dump(self, obj: Any) -> tuple[str, bytes]:
        if hasattr(self.serde, "dumps_typed"):
            return self.serde.dumps_typed(obj)
        return ("json", self.serde.dumps(obj))

    def _load(self, type_name: str, data: bytes) -> Any:
        if hasattr(self.serde, "loads_typed"):
            return self.serde.loads_typed((type_name, data))
        return self.serde.loads(data)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        raise NotImplementedError("Use aget_tuple in asynchronous context")

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        raise NotImplementedError("Use alist in asynchronous context")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        raise NotImplementedError("Use aput in asynchronous context")

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        raise NotImplementedError("Use aput_writes in asynchronous context")

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")

        query: dict[str, Any] = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
        }
        if checkpoint_id:
            query["checkpoint_id"] = checkpoint_id

        doc = None
        if await _check_mongo_connection():
            try:
                doc = await self.checkpoints.find_one(query, sort=[("_id", -1)])
            except Exception:
                doc = None

        if not doc:
            candidates = [
                d for d in self._mem_checkpoints.values()
                if d.get("thread_id") == thread_id
                and d.get("checkpoint_ns") == checkpoint_ns
                and (not checkpoint_id or d.get("checkpoint_id") == checkpoint_id)
            ]
            if candidates:
                doc = candidates[-1]

        if not doc:
            return None

        checkpoint = self._load(doc.get("type", "json"), doc["checkpoint"])
        metadata = self._load(doc.get("metadata_type", "json"), doc["metadata"]) if doc.get("metadata") else {}

        pending_writes = []
        if await _check_mongo_connection():
            try:
                writes_cursor = self.writes.find(
                    {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": doc["checkpoint_id"],
                    }
                ).sort("idx", 1)
                async for w_doc in writes_cursor:
                    val = self._load(w_doc.get("type", "json"), w_doc["value"])
                    pending_writes.append((w_doc["task_id"], w_doc["channel"], val))
            except Exception:
                pending_writes = []

        if not pending_writes:
            mem_w = [
                w for w in self._mem_writes
                if w.get("thread_id") == thread_id
                and w.get("checkpoint_ns") == checkpoint_ns
                and w.get("checkpoint_id") == doc["checkpoint_id"]
            ]
            for w_doc in mem_w:
                val = self._load(w_doc.get("type", "json"), w_doc["value"])
                pending_writes.append((w_doc["task_id"], w_doc["channel"], val))

        parent_config = None
        if doc.get("parent_checkpoint_id"):
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": doc["parent_checkpoint_id"],
                }
            }

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": doc["checkpoint_id"],
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes if pending_writes else None,
        )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        query: dict[str, Any] = {}
        thread_id = None
        checkpoint_ns = None
        if config:
            configurable = config.get("configurable", {})
            if "thread_id" in configurable:
                thread_id = configurable["thread_id"]
                query["thread_id"] = thread_id
            if "checkpoint_ns" in configurable:
                checkpoint_ns = configurable["checkpoint_ns"]
                query["checkpoint_ns"] = checkpoint_ns

        if await _check_mongo_connection():
            try:
                cursor = self.checkpoints.find(query).sort("_id", -1)
                if limit:
                    cursor = cursor.limit(limit)

                async for doc in cursor:
                    checkpoint = self._load(doc.get("type", "json"), doc["checkpoint"])
                    metadata = self._load(doc.get("metadata_type", "json"), doc["metadata"]) if doc.get("metadata") else {}
                    yield CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": doc["thread_id"],
                                "checkpoint_ns": doc["checkpoint_ns"],
                                "checkpoint_id": doc["checkpoint_id"],
                            }
                        },
                        checkpoint=checkpoint,
                        metadata=metadata,
                        parent_config={
                            "configurable": {
                                "thread_id": doc["thread_id"],
                                "checkpoint_ns": doc["checkpoint_ns"],
                                "checkpoint_id": doc["parent_checkpoint_id"],
                            }
                        } if doc.get("parent_checkpoint_id") else None,
                    )
                return
            except Exception:
                pass

        candidates = [
            d for d in self._mem_checkpoints.values()
            if (not thread_id or d.get("thread_id") == thread_id)
            and (not checkpoint_ns or d.get("checkpoint_ns") == checkpoint_ns)
        ]
        for doc in reversed(candidates):
            checkpoint = self._load(doc.get("type", "json"), doc["checkpoint"])
            metadata = self._load(doc.get("metadata_type", "json"), doc["metadata"]) if doc.get("metadata") else {}
            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": doc["thread_id"],
                        "checkpoint_ns": doc["checkpoint_ns"],
                        "checkpoint_id": doc["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config={
                    "configurable": {
                        "thread_id": doc["thread_id"],
                        "checkpoint_ns": doc["checkpoint_ns"],
                        "checkpoint_id": doc["parent_checkpoint_id"],
                    }
                } if doc.get("parent_checkpoint_id") else None,
            )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> RunnableConfig:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = configurable.get("checkpoint_id")

        c_type, c_bytes = self._dump(checkpoint)
        m_type, m_bytes = self._dump(metadata)

        doc = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "type": c_type,
            "checkpoint": c_bytes,
            "metadata_type": m_type,
            "metadata": m_bytes,
        }

        saved_to_mongo = False
        if await _check_mongo_connection():
            try:
                await self.checkpoints.update_one(
                    {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": checkpoint_id,
                    },
                    {"$set": doc},
                    upsert=True,
                )
                saved_to_mongo = True
            except Exception:
                saved_to_mongo = False

        if not saved_to_mongo:
            key = f"{thread_id}:{checkpoint_ns}:{checkpoint_id}"
            self._mem_checkpoints[key] = doc

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")

        for idx, (channel, val) in enumerate(writes):
            val_type, val_bytes = self._dump(val)
            doc = {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "idx": idx,
                "channel": channel,
                "type": val_type,
                "value": val_bytes,
            }
            saved_to_mongo = False
            if await _check_mongo_connection():
                try:
                    await self.writes.update_one(
                        {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                            "task_id": task_id,
                            "idx": idx,
                        },
                        {"$set": doc},
                        upsert=True,
                    )
                    saved_to_mongo = True
                except Exception:
                    saved_to_mongo = False

            if not saved_to_mongo:
                self._mem_writes.append(doc)
