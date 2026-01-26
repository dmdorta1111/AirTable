"""Unit tests for TextFieldHandler."""

import pytest

from pybase.fields.types.text import TextFieldHandler


class TestTextFieldHandler:
    """Tests for TextFieldHandler class."""

    def test_field_type(self):
        """Test field type identifier."""
        assert TextFieldHandler.field_type == "text"


class TestTextSerialization:
    """Tests for text serialization."""

    def test_serialize_none(self):
        """Test serializing None returns None."""
        result = TextFieldHandler.serialize(None)
        assert result is None

    def test_serialize_string(self):
        """Test serializing a string returns it unchanged."""
        result = TextFieldHandler.serialize("hello world")
        assert result == "hello world"

    def test_serialize_empty_string(self):
        """Test serializing empty string."""
        result = TextFieldHandler.serialize("")
        assert result == ""

    def test_serialize_integer(self):
        """Test serializing an integer converts to string."""
        result = TextFieldHandler.serialize(123)
        assert result == "123"
        assert isinstance(result, str)

    def test_serialize_float(self):
        """Test serializing a float converts to string."""
        result = TextFieldHandler.serialize(123.456)
        assert result == "123.456"
        assert isinstance(result, str)

    def test_serialize_boolean(self):
        """Test serializing a boolean converts to string."""
        result = TextFieldHandler.serialize(True)
        assert result == "True"
        assert isinstance(result, str)

        result = TextFieldHandler.serialize(False)
        assert result == "False"
        assert isinstance(result, str)

    def test_serialize_unicode(self):
        """Test serializing unicode characters."""
        result = TextFieldHandler.serialize("Hello 世界 🌍")
        assert result == "Hello 世界 🌍"

    def test_serialize_multiline(self):
        """Test serializing multiline string."""
        text = "Line 1\nLine 2\nLine 3"
        result = TextFieldHandler.serialize(text)
        assert result == text


class TestTextDeserialization:
    """Tests for text deserialization."""

    def test_deserialize_none(self):
        """Test deserializing None returns None."""
        result = TextFieldHandler.deserialize(None)
        assert result is None

    def test_deserialize_string(self):
        """Test deserializing a string returns it unchanged."""
        result = TextFieldHandler.deserialize("hello world")
        assert result == "hello world"

    def test_deserialize_empty_string(self):
        """Test deserializing empty string."""
        result = TextFieldHandler.deserialize("")
        assert result == ""

    def test_deserialize_integer(self):
        """Test deserializing an integer converts to string."""
        result = TextFieldHandler.deserialize(123)
        assert result == "123"
        assert isinstance(result, str)

    def test_deserialize_float(self):
        """Test deserializing a float converts to string."""
        result = TextFieldHandler.deserialize(123.456)
        assert result == "123.456"
        assert isinstance(result, str)


class TestTextValidation:
    """Tests for text validation."""

    def test_validate_none(self):
        """Test validating None is allowed."""
        assert TextFieldHandler.validate(None) is True

    def test_validate_valid_string(self):
        """Test validating valid string."""
        assert TextFieldHandler.validate("hello world") is True

    def test_validate_empty_string(self):
        """Test validating empty string is allowed by default."""
        assert TextFieldHandler.validate("") is True

    def test_validate_non_string_fails(self):
        """Test validating non-string type raises error."""
        with pytest.raises(ValueError, match="Text field requires string value"):
            TextFieldHandler.validate(123)

        with pytest.raises(ValueError, match="Text field requires string value"):
            TextFieldHandler.validate([1, 2, 3])

        with pytest.raises(ValueError, match="Text field requires string value"):
            TextFieldHandler.validate({"key": "value"})


class TestTextLengthValidation:
    """Tests for text length validation."""

    def test_validate_max_length_pass(self):
        """Test validation passes with value under max_length."""
        options = {"max_length": 10}
        assert TextFieldHandler.validate("hello", options) is True

    def test_validate_max_length_exact(self):
        """Test validation passes with value at exact max_length."""
        options = {"max_length": 5}
        assert TextFieldHandler.validate("hello", options) is True

    def test_validate_max_length_fail(self):
        """Test validation fails when exceeding max_length."""
        options = {"max_length": 5}
        with pytest.raises(ValueError, match="exceeds max length of 5"):
            TextFieldHandler.validate("hello world", options)

    def test_validate_default_max_length(self):
        """Test default max_length is 255."""
        long_string = "a" * 255
        assert TextFieldHandler.validate(long_string) is True

        too_long_string = "a" * 256
        with pytest.raises(ValueError, match="exceeds max length of 255"):
            TextFieldHandler.validate(too_long_string)

    def test_validate_min_length_pass(self):
        """Test validation passes with value over min_length."""
        options = {"min_length": 5}
        assert TextFieldHandler.validate("hello world", options) is True

    def test_validate_min_length_exact(self):
        """Test validation passes with value at exact min_length."""
        options = {"min_length": 5}
        assert TextFieldHandler.validate("hello", options) is True

    def test_validate_min_length_fail(self):
        """Test validation fails when below min_length."""
        options = {"min_length": 5}
        with pytest.raises(ValueError, match="is below min length of 5"):
            TextFieldHandler.validate("hi", options)

    def test_validate_min_length_zero_default(self):
        """Test default min_length is 0."""
        assert TextFieldHandler.validate("", {}) is True

    def test_validate_min_and_max_length(self):
        """Test validation with both min and max length constraints."""
        options = {"min_length": 5, "max_length": 10}

        # Too short
        with pytest.raises(ValueError, match="is below min length of 5"):
            TextFieldHandler.validate("hi", options)

        # Just right
        assert TextFieldHandler.validate("hello", options) is True
        assert TextFieldHandler.validate("helloworld", options) is True

        # Too long
        with pytest.raises(ValueError, match="exceeds max length of 10"):
            TextFieldHandler.validate("hello world", options)


class TestTextRegexValidation:
    """Tests for regex validation."""

    def test_validate_regex_simple_match(self):
        """Test regex validation with simple pattern match."""
        options = {"regex": r"^hello"}
        assert TextFieldHandler.validate("hello world", options) is True

    def test_validate_regex_simple_no_match(self):
        """Test regex validation fails when pattern doesn't match."""
        options = {"regex": r"^hello"}
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("world hello", options)

    def test_validate_regex_email_pattern(self):
        """Test regex validation with email pattern."""
        options = {"regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"}

        # Valid emails
        assert TextFieldHandler.validate("user@example.com", options) is True
        assert TextFieldHandler.validate("test.user+tag@domain.co.uk", options) is True

        # Invalid emails
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("invalid-email", options)

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("@example.com", options)

    def test_validate_regex_phone_pattern(self):
        """Test regex validation with phone number pattern."""
        options = {"regex": r"^\d{3}-\d{3}-\d{4}$"}

        # Valid phone
        assert TextFieldHandler.validate("555-123-4567", options) is True

        # Invalid phone
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("555-1234-567", options)

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("5551234567", options)

    def test_validate_regex_alphanumeric(self):
        """Test regex validation with alphanumeric pattern."""
        options = {"regex": r"^[a-zA-Z0-9]+$"}

        # Valid
        assert TextFieldHandler.validate("abc123", options) is True
        assert TextFieldHandler.validate("ABC", options) is True
        assert TextFieldHandler.validate("123", options) is True

        # Invalid (contains special characters)
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("abc-123", options)

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("abc 123", options)

    def test_validate_regex_url_pattern(self):
        """Test regex validation with URL pattern."""
        options = {"regex": r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"}

        # Valid URLs
        assert TextFieldHandler.validate("http://example.com", options) is True
        assert TextFieldHandler.validate("https://www.example.com/path", options) is True

        # Invalid URLs
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("example.com", options)

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("ftp://example.com", options)

    def test_validate_regex_case_sensitive(self):
        """Test regex validation is case-sensitive by default."""
        options = {"regex": r"^HELLO"}

        assert TextFieldHandler.validate("HELLO world", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("hello world", options)

    def test_validate_regex_case_insensitive_flag(self):
        """Test regex validation with case-insensitive flag."""
        options = {"regex": r"(?i)^hello"}

        assert TextFieldHandler.validate("HELLO world", options) is True
        assert TextFieldHandler.validate("hello world", options) is True
        assert TextFieldHandler.validate("HeLLo world", options) is True

    def test_validate_regex_digits_only(self):
        """Test regex validation for digits only."""
        options = {"regex": r"^\d+$"}

        assert TextFieldHandler.validate("12345", options) is True
        assert TextFieldHandler.validate("0", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("123abc", options)

    def test_validate_regex_no_special_chars(self):
        """Test regex validation excluding special characters."""
        options = {"regex": r"^[a-zA-Z0-9\s]+$"}

        assert TextFieldHandler.validate("Hello World 123", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("Hello@World", options)

    def test_validate_regex_exact_length(self):
        """Test regex validation for exact length."""
        options = {"regex": r"^.{5}$"}

        assert TextFieldHandler.validate("abcde", options) is True
        assert TextFieldHandler.validate("12345", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("abc", options)

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("abcdef", options)

    def test_validate_regex_with_groups(self):
        """Test regex validation with capture groups."""
        options = {"regex": r"^(\d{2})-([A-Z]{3})-(\d{4})$"}

        assert TextFieldHandler.validate("12-ABC-2023", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("12-abc-2023", options)

    def test_validate_regex_empty_string(self):
        """Test regex validation with empty string."""
        options = {"regex": r"^$"}

        assert TextFieldHandler.validate("", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("non-empty", options)

    def test_validate_regex_multiline(self):
        """Test regex validation with multiline pattern."""
        options = {"regex": r"^Line \d+$"}

        # Single line matches
        assert TextFieldHandler.validate("Line 1", options) is True

        # Multi-line doesn't match (without multiline flag)
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("Line 1\nLine 2", options)

    def test_validate_invalid_regex_pattern(self):
        """Test validation with invalid regex pattern raises error."""
        options = {"regex": r"[unclosed"}

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            TextFieldHandler.validate("test", options)

    def test_validate_regex_with_backslash_escape(self):
        """Test regex validation with escaped characters."""
        options = {"regex": r"^test\.txt$"}

        assert TextFieldHandler.validate("test.txt", options) is True

        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("testXtxt", options)

    def test_validate_regex_optional_pattern(self):
        """Test regex validation with optional groups."""
        options = {"regex": r"^https?://(www\.)?example\.com$"}

        assert TextFieldHandler.validate("http://example.com", options) is True
        assert TextFieldHandler.validate("https://www.example.com", options) is True
        assert TextFieldHandler.validate("http://www.example.com", options) is True

    def test_validate_regex_with_none_value(self):
        """Test regex validation with None value passes."""
        options = {"regex": r"^\d+$"}
        assert TextFieldHandler.validate(None, options) is True


class TestTextRegexWithOtherValidations:
    """Tests for regex validation combined with other validations."""

    def test_validate_regex_and_length(self):
        """Test regex validation combined with length validation."""
        options = {
            "regex": r"^\d+$",
            "min_length": 3,
            "max_length": 5
        }

        # Valid - matches regex and length constraints
        assert TextFieldHandler.validate("123", options) is True
        assert TextFieldHandler.validate("12345", options) is True

        # Invalid - too short
        with pytest.raises(ValueError, match="is below min length"):
            TextFieldHandler.validate("12", options)

        # Invalid - too long
        with pytest.raises(ValueError, match="exceeds max length"):
            TextFieldHandler.validate("123456", options)

        # Invalid - doesn't match regex
        with pytest.raises(ValueError, match="does not match required pattern"):
            TextFieldHandler.validate("abc", options)

    def test_validate_non_string_before_regex(self):
        """Test that type validation occurs before regex validation."""
        options = {"regex": r"^\d+$"}

        # Should fail with type error, not regex error
        with pytest.raises(ValueError, match="Text field requires string value"):
            TextFieldHandler.validate(123, options)


class TestTextDefault:
    """Tests for text default value."""

    def test_default(self):
        """Test default value is empty string."""
        result = TextFieldHandler.default()
        assert result == ""
        assert isinstance(result, str)


def test_min_length():
    """Comprehensive test for min_length validation option.

    Test cases:
    - Value at exact min_length (should pass)
    - Value below min_length (should fail)
    - Value above min_length (should pass)
    - None value (should pass)
    """
    # Test value at exact min_length - should pass
    options = {"min_length": 5}
    assert TextFieldHandler.validate("hello", options) is True

    # Test value below min_length - should fail
    with pytest.raises(ValueError, match="is below min length of 5"):
        TextFieldHandler.validate("hi", options)

    # Test value above min_length - should pass
    assert TextFieldHandler.validate("hello world", options) is True

    # Test None value - should pass (None values bypass validation)
    assert TextFieldHandler.validate(None, options) is True


def test_combined_validations():
    """Comprehensive test for combined validation options.

    Test cases:
    - min_length + max_length combined
    - regex + min_length combined
    - regex + max_length combined
    - min_length + max_length + regex all combined
    - None value with combined options (should pass)
    """
    # Test min_length + max_length combined
    options = {"min_length": 3, "max_length": 8}

    # Valid values within range
    assert TextFieldHandler.validate("abc", options) is True
    assert TextFieldHandler.validate("abcde", options) is True
    assert TextFieldHandler.validate("abcdefgh", options) is True

    # Too short - should fail with min_length error
    with pytest.raises(ValueError, match="is below min length of 3"):
        TextFieldHandler.validate("ab", options)

    # Too long - should fail with max_length error
    with pytest.raises(ValueError, match="exceeds max length of 8"):
        TextFieldHandler.validate("abcdefghi", options)

    # Test regex + min_length combined
    options = {"regex": r"^\d+$", "min_length": 3}

    # Valid - matches regex and meets min_length
    assert TextFieldHandler.validate("123", options) is True
    assert TextFieldHandler.validate("12345", options) is True

    # Too short - should fail with min_length error
    with pytest.raises(ValueError, match="is below min length of 3"):
        TextFieldHandler.validate("12", options)

    # Doesn't match regex - should fail with regex error
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("abc", options)

    # Doesn't match regex even with sufficient length
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("abc123", options)

    # Test regex + max_length combined
    options = {"regex": r"^[A-Z]+$", "max_length": 5}

    # Valid - matches regex and within max_length
    assert TextFieldHandler.validate("ABC", options) is True
    assert TextFieldHandler.validate("ABCDE", options) is True

    # Too long - should fail with max_length error
    with pytest.raises(ValueError, match="exceeds max length of 5"):
        TextFieldHandler.validate("ABCDEF", options)

    # Doesn't match regex - should fail with regex error
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("abc", options)

    # Doesn't match regex (contains lowercase)
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("ABc", options)

    # Test all three combined: min_length + max_length + regex
    options = {
        "regex": r"^[A-Z]{3}\d{3}$",
        "min_length": 6,
        "max_length": 6
    }

    # Valid - matches all constraints (format ABC123)
    assert TextFieldHandler.validate("ABC123", options) is True
    assert TextFieldHandler.validate("XYZ789", options) is True

    # Too short - fails min_length
    with pytest.raises(ValueError, match="is below min length of 6"):
        TextFieldHandler.validate("AB12", options)

    # Too long - fails max_length
    with pytest.raises(ValueError, match="exceeds max length of 6"):
        TextFieldHandler.validate("ABC1234", options)

    # Wrong format - fails regex (lowercase letters)
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("abc123", options)

    # Wrong format - fails regex (letters not at start)
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("123ABC", options)

    # Wrong format - fails regex (wrong structure)
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("AB1234", options)

    # Test None value with combined options - should pass
    options = {
        "regex": r"^\d+$",
        "min_length": 5,
        "max_length": 10
    }
    assert TextFieldHandler.validate(None, options) is True

    # Test complex real-world pattern: email-like with length constraints
    options = {
        "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "min_length": 10,
        "max_length": 50
    }

    # Valid email within length constraints
    assert TextFieldHandler.validate("user@example.com", options) is True
    assert TextFieldHandler.validate("test.user+tag@domain.co.uk", options) is True

    # Too short (even if matches regex format)
    with pytest.raises(ValueError, match="is below min length of 10"):
        TextFieldHandler.validate("a@b.cd", options)

    # Too long - exceeds max_length
    long_email = "verylongemailaddress123456789@verylongdomainname123456789.com"
    with pytest.raises(ValueError, match="exceeds max length of 50"):
        TextFieldHandler.validate(long_email, options)

    # Invalid email format
    with pytest.raises(ValueError, match="does not match required pattern"):
        TextFieldHandler.validate("invalid-email", options)
