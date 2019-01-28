from .projectparser import ProjectParser

def test_notfound():
    try:
        parser = ProjectParser("test_data/NonExistingFile")
        assert not parser.getI()
        assert not parser.getQ()
        assert len(parser.getR()) == 1
    except FileNotFoundError:
        pass

def test_empty():
    parser = ProjectParser("test_data/emptyCoqProject")
    assert not parser.getI()
    assert not parser.getQ()
    assert len(parser.getR()) == 0

def test_some():
    parser = ProjectParser("test_data/_CoqProject")
    assert not parser.getQ()
    assert len(parser.getI()) == 1
    assert parser.getI()[0] == "/usr/local/lib"
    assert len(parser.getR()) == 11
