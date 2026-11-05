from scripts.install_skill import install


def test_install_copies_skill_and_standard(tmp_path):
    dest = install(tmp_path)
    assert dest == tmp_path / "po-spec-review"
    skill = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: po-spec-review\n")
    assert (dest / "standard.pt-BR.md").read_text(encoding="utf-8").startswith("# Padrão de especificação")
    assert (dest / "scripts" / "stories_pdf.py").exists()


def test_install_twice_overwrites(tmp_path):
    install(tmp_path)
    (tmp_path / "po-spec-review" / "SKILL.md").write_text("old", encoding="utf-8")
    install(tmp_path)
    assert (tmp_path / "po-spec-review" / "SKILL.md").read_text(encoding="utf-8").startswith("---")
