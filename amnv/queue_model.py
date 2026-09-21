from collections import deque

from amnv.config_loader import load_validation_config
from amnv.models import CQEntry, SQEntry


class QueueModel:
    def __init__(self):
        config = load_validation_config()

        self.sq_depth = config["queue"]["sq_depth"]
        self.cq_depth = config["queue"]["cq_depth"]

        self.cid_start = config["cid"]["start"]
        self.cid_increment = config["cid"]["increment"]

        self.sq = deque(maxlen=self.sq_depth)
        self.cq = deque(maxlen=self.cq_depth)

        self.sq_head = 0
        self.sq_tail = 0

        self.cq_head = 0
        self.cq_tail = 0

        self.next_cid = self.cid_start

        # 尚未完成的 Command CID。
        self.outstanding_cids: set[int] = set()

    def allocate_cid(self) -> int:
        cid = self.next_cid

        while cid in self.outstanding_cids:
            cid += self.cid_increment

        self.next_cid = cid + self.cid_increment

        return cid

    def host_submit_command(
        self,
        opcode: str,
        nsid: int = 1,
        lba: int | None = None,
        length: int | None = None,
        data=None,
        cid: int | None = None,
    ) -> SQEntry:

        if len(self.sq) >= self.sq_depth:
            raise RuntimeError(
                "Submission Queue is full."
            )

        if cid is None:
            cid = self.allocate_cid()

        if cid in self.outstanding_cids:
            raise RuntimeError(
                f"CID {cid} is already outstanding."
            )

        # 若 Host 手動指定較大的 CID，
        # 後續自動配置不可倒退產生相同 CID。
        if cid >= self.next_cid:
            self.next_cid = (
                cid + self.cid_increment
            )

        entry = SQEntry(
            cid=cid,
            opcode=opcode,
            nsid=nsid,
            lba=lba,
            length=length,
            data=data,
        )

        self.sq.append(entry)
        self.outstanding_cids.add(cid)

        # Host updates SQ Tail.
        self.sq_tail = (
            self.sq_tail + 1
        ) % self.sq_depth

        return entry

    def controller_fetch_command(
        self
    ) -> SQEntry | None:

        if not self.sq:
            return None

        entry = self.sq.popleft()

        # Controller advances SQ Head.
        self.sq_head = (
            self.sq_head + 1
        ) % self.sq_depth

        return entry

    def controller_post_completion(
        self,
        completion: CQEntry,
    ) -> None:

        if len(self.cq) >= self.cq_depth:
            raise RuntimeError(
                "Completion Queue is full."
            )

        if completion.cid not in self.outstanding_cids:
            raise RuntimeError(
                f"Completion CID {completion.cid} "
                "does not match an outstanding command."
            )

        # Completion records current logical SQ Head.
        completion.sq_head = self.sq_head

        self.cq.append(completion)

        # Controller advances CQ Tail.
        self.cq_tail = (
            self.cq_tail + 1
        ) % self.cq_depth

    def host_consume_completion(
        self
    ) -> CQEntry | None:

        if not self.cq:
            return None

        completion = self.cq.popleft()

        # Host advances CQ Head.
        self.cq_head = (
            self.cq_head + 1
        ) % self.cq_depth

        self.outstanding_cids.discard(
            completion.cid
        )

        return completion

    def reset_controller_state(
        self
    ) -> None:

        self.sq.clear()
        self.cq.clear()

        self.outstanding_cids.clear()

        self.sq_head = 0
        self.sq_tail = 0

        self.cq_head = 0
        self.cq_tail = 0

        # 同一個 Test / Case 內：
        # Controller Reset 不重置 CID progression.