import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("feeder", Path(__file__).parent.parent / "scripts/feeder.py")
feeder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feeder)


def test_take_line_pops_each_job_once_in_file_order(tmp_path):
    (tmp_path / "a.txt").write_text("# note\njob one\n\njob two\n")
    (tmp_path / "b.txt").write_text("job three\n")
    assert [feeder.take_line(tmp_path) for _ in range(4)] == ["job one", "job two", "job three", None]
    assert "job" not in (tmp_path / "a.txt").read_text()
