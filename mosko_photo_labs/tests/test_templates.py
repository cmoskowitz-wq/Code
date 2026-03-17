"""
test_templates.py — Mosko Photo Labs
Unit tests for the template management system.
"""

import json
import pytest
from pathlib import Path

from app.core.templates import ExifTemplate, TemplateManager


# ── ExifTemplate ───────────────────────────────────────────────────────────

class TestExifTemplate:
    def test_creation(self):
        t = ExifTemplate(name="My Template",
                         description="Test desc",
                         fields={"Artist": "Alice"})
        assert t.name == "My Template"
        assert t.description == "Test desc"
        assert t.fields["Artist"] == "Alice"

    def test_to_dict(self):
        t = ExifTemplate(name="T1", description="D1", fields={"k": "v"})
        d = t.to_dict()
        assert d["name"] == "T1"
        assert d["description"] == "D1"
        assert d["fields"]["k"] == "v"

    def test_from_dict(self):
        d = {"name": "T2", "description": "D2", "fields": {"a": 1}}
        t = ExifTemplate.from_dict(d)
        assert t.name == "T2"
        assert t.fields["a"] == 1

    def test_from_dict_missing_keys(self):
        t = ExifTemplate.from_dict({})
        assert t.name == "Unnamed"
        assert t.fields == {}

    def test_roundtrip(self):
        original = ExifTemplate(
            name="Roundtrip",
            description="desc",
            fields={"Artist": "Bob", "GPSLatitude": 40.75},
        )
        restored = ExifTemplate.from_dict(original.to_dict())
        assert restored.name == original.name
        assert restored.fields == original.fields


# ── TemplateManager ────────────────────────────────────────────────────────

class TestTemplateManager:
    def test_empty_on_new_file(self, template_manager):
        assert template_manager.templates == []

    def test_add_template(self, template_manager):
        t = ExifTemplate(name="T1", fields={"Artist": "X"})
        template_manager.add(t)
        assert len(template_manager.templates) == 1
        assert template_manager.templates[0].name == "T1"

    def test_add_persists_to_disk(self, template_manager, tmp_path):
        t = ExifTemplate(name="Persist", fields={"Artist": "P"})
        template_manager.add(t)
        # Create a fresh manager pointing at the same file
        mgr2 = TemplateManager(template_manager.filepath)
        assert any(t.name == "Persist" for t in mgr2.templates)

    def test_get_by_name(self, template_manager):
        template_manager.add(ExifTemplate(name="FindMe", fields={"k": "v"}))
        found = template_manager.get("FindMe")
        assert found is not None
        assert found.name == "FindMe"

    def test_get_nonexistent_returns_none(self, template_manager):
        assert template_manager.get("Nope") is None

    def test_names_property(self, template_manager):
        template_manager.add(ExifTemplate(name="A"))
        template_manager.add(ExifTemplate(name="B"))
        assert "A" in template_manager.names
        assert "B" in template_manager.names

    def test_delete_template(self, template_manager):
        template_manager.add(ExifTemplate(name="ToDelete"))
        result = template_manager.delete("ToDelete")
        assert result is True
        assert template_manager.get("ToDelete") is None

    def test_delete_nonexistent_returns_false(self, template_manager):
        result = template_manager.delete("Ghost")
        assert result is False

    def test_replace_existing_name(self, template_manager):
        template_manager.add(ExifTemplate(name="Dup", fields={"a": 1}))
        template_manager.add(ExifTemplate(name="Dup", fields={"a": 2}))
        assert len(template_manager.templates) == 1
        assert template_manager.get("Dup").fields["a"] == 2

    def test_rename(self, template_manager):
        template_manager.add(ExifTemplate(name="Old"))
        result = template_manager.rename("Old", "New")
        assert result is True
        assert template_manager.get("New") is not None
        assert template_manager.get("Old") is None

    def test_rename_nonexistent_returns_false(self, template_manager):
        assert template_manager.rename("Ghost", "X") is False

    def test_multiple_templates(self, template_manager):
        for i in range(5):
            template_manager.add(ExifTemplate(name=f"T{i}", fields={"ISO": i * 100}))
        assert len(template_manager.templates) == 5

    def test_load_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ not valid json !!!")
        mgr = TemplateManager(bad_file)
        assert mgr.templates == []

    def test_builtin_templates_seeded(self, tmp_path):
        mgr = TemplateManager(tmp_path / "builtins.json")
        mgr.add_builtin_templates()
        assert len(mgr.templates) >= 3
        names = mgr.names
        assert any("Copyright" in n for n in names)
        assert any("GPS" in n or "Lens" in n or "Sony" in n or "Canon" in n
                   for n in names)

    def test_builtins_not_seeded_twice(self, tmp_path):
        mgr = TemplateManager(tmp_path / "once.json")
        mgr.add_builtin_templates()
        n = len(mgr.templates)
        mgr.add_builtin_templates()
        assert len(mgr.templates) == n  # No duplicates


# ── Image model integration ────────────────────────────────────────────────

class TestImageModelWithTemplates:
    def test_apply_template_to_collection(self, folder_with_images, template_manager):
        from app.models.image_model import ImageCollection
        col = ImageCollection()
        col.load_folder(folder_with_images)

        template = ExifTemplate(
            name="Batch Copyright",
            fields={"Artist": "Studio X", "Copyright": "© 2026 Studio X"},
        )
        template_manager.add(template)

        col.select_all()
        count = col.apply_to_selection(template.fields)

        assert count == 5
        for img in col:
            # apply_to_selection already called load_exif + set_fields internally;
            # do NOT reload from disk — check in-memory state only
            assert img.exif.get("Artist") == "Studio X"
            assert img.is_dirty
