import pytest
from benchpro.core.templating import TemplateEngine

def test_render_string():
    engine = TemplateEngine({"var": "world"})
    assert engine.render("Hello ${var}") == "Hello world"

def test_render_dict():
    engine = TemplateEngine({"var": "value"})
    data = {"key": "val is ${var}"}
    assert engine.render(data) == {"key": "val is value"}

def test_render_nested():
    engine = TemplateEngine({"a": {"b": "nested"}})
    assert engine.render("This is ${a.b}") == "This is nested"

def test_render_missing_var():
    engine = TemplateEngine({})
    with pytest.raises(ValueError):
        engine.render("Hello ${missing}")
