import pytest

from atlas.lsm import LSMTree


def test_transaction_commit(tmp_path):
    db = LSMTree(tmp_path)
    with db.transaction() as tx:
        tx.put("name", "Atlas")
        tx.put("version", 1)
    assert db.get("name") == "Atlas"
    assert db.get("version") == 1
    db.close()


def test_transaction_rollback_on_exception(tmp_path):
    db = LSMTree(tmp_path)
    with pytest.raises(RuntimeError), db.transaction() as tx:
        tx.put("name", "Atlas")
        raise RuntimeError("rollback")
    assert db.get("name") is None
    db.close()


def test_transaction_reads_its_own_writes(tmp_path):
    db = LSMTree(tmp_path)
    with db.transaction() as tx:
        tx.put("name", "Atlas")
        assert tx.get("name") == "Atlas"
    db.close()


def test_transaction_commit_survives_restart(tmp_path):
    db = LSMTree(tmp_path)
    with db.transaction() as tx:
        tx.put("balance", 500)
    db.close()

    db = LSMTree(tmp_path)
    assert db.get("balance") == 500
    db.close()


def test_transaction_cannot_be_reused_after_commit(tmp_path):
    db = LSMTree(tmp_path)
    tx = db.transaction()
    tx.put("key", "value")
    tx.commit()

    with pytest.raises(RuntimeError):
        tx.put("another", "value")

    db.close()
