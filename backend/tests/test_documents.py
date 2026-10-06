from pathlib import Path

from indexmind.documents import is_supported, read_sections, split_markdown


def test_markdown_sections_carry_heading_trail():
    text = "# Guide\nintro\n## Install\nrun it\n## Usage\nuse it\n# Other\nmore"

    sections = split_markdown(text)

    assert [(s.heading, s.text) for s in sections] == [
        ("Guide", "intro"),
        ("Guide / Install", "run it"),
        ("Guide / Usage", "use it"),
        ("Other", "more"),
    ]


def test_markdown_ignores_hashes_inside_code_fences():
    text = "# Script\n```sh\n# not a heading\necho hi\n```"

    sections = split_markdown(text)

    assert len(sections) == 1
    assert "# not a heading" in sections[0].text


def test_plain_text_is_one_section(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("hello world")

    assert [s.text for s in read_sections(path)] == ["hello world"]


def test_is_supported_filters_by_suffix_and_hidden_files(tmp_path: Path):
    for name in ["a.pdf", "b.MD", "c.txt", "d.docx", ".hidden.md"]:
        (tmp_path / name).write_text("x")

    supported = sorted(p.name for p in tmp_path.iterdir() if is_supported(p))

    assert supported == ["a.pdf", "b.MD", "c.txt"]
