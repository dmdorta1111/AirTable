"""Unit tests for ThreadFieldHandler."""

import pytest

from pybase.fields.types.engineering.thread import ThreadFieldHandler


class TestThreadFieldHandler:
    """Tests for ThreadFieldHandler class."""

    def test_field_type(self):
        """Test field type identifier."""
        assert ThreadFieldHandler.field_type == "thread"

    def test_standards_defined(self):
        """Test that thread standards are properly defined."""
        assert "metric" in ThreadFieldHandler.STANDARDS
        assert "unc" in ThreadFieldHandler.STANDARDS
        assert "unf" in ThreadFieldHandler.STANDARDS
        assert "unef" in ThreadFieldHandler.STANDARDS
        assert "bsp" in ThreadFieldHandler.STANDARDS
        assert "npt" in ThreadFieldHandler.STANDARDS
        assert "acme" in ThreadFieldHandler.STANDARDS
        assert "buttress" in ThreadFieldHandler.STANDARDS

    def test_metric_coarse_pitch_defined(self):
        """Test that metric coarse pitches are properly defined."""
        assert ThreadFieldHandler.METRIC_COARSE_PITCH[8] == 1.25
        assert ThreadFieldHandler.METRIC_COARSE_PITCH[10] == 1.5
        assert ThreadFieldHandler.METRIC_COARSE_PITCH[12] == 1.75
        assert ThreadFieldHandler.METRIC_COARSE_PITCH[6] == 1

    def test_unc_standard_defined(self):
        """Test that UNC standard sizes are properly defined."""
        assert ThreadFieldHandler.UNC_STANDARD[0.25] == 20
        assert ThreadFieldHandler.UNC_STANDARD[0.5] == 13
        assert ThreadFieldHandler.UNC_STANDARD[0.75] == 10

    def test_unf_standard_defined(self):
        """Test that UNF standard sizes are properly defined."""
        assert ThreadFieldHandler.UNF_STANDARD[0.25] == 28
        assert ThreadFieldHandler.UNF_STANDARD[0.5] == 20
        assert ThreadFieldHandler.UNF_STANDARD[0.75] == 16

    def test_thread_classes_defined(self):
        """Test that thread classes are properly defined."""
        assert "6g" in ThreadFieldHandler.METRIC_THREAD_CLASSES
        assert "6h" in ThreadFieldHandler.METRIC_THREAD_CLASSES
        assert "2a" in ThreadFieldHandler.UNIFIED_THREAD_CLASSES
        assert "2b" in ThreadFieldHandler.UNIFIED_THREAD_CLASSES


class TestThreadSerialization:
    """Tests for thread serialization."""

    def test_serialize_none(self):
        """Test serializing None returns None."""
        result = ThreadFieldHandler.serialize(None)
        assert result is None

    def test_serialize_dict_metric(self):
        """Test serializing a metric thread dict."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "class": "6g",
            "internal": False,
            "left_hand": False,
        }
        result = ThreadFieldHandler.serialize(value)
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25
        assert result["class"] == "6g"
        assert result["internal"] is False
        assert result["left_hand"] is False

    def test_serialize_dict_unc(self):
        """Test serializing a UNC thread dict."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "2a",
            "internal": False,
            "left_hand": False,
        }
        result = ThreadFieldHandler.serialize(value)
        assert result["standard"] == "unc"
        assert result["size"] == 0.25
        assert result["tpi"] == 20
        assert result["class"] == "2a"

    def test_serialize_dict_defaults(self):
        """Test serializing dict with missing optional fields."""
        value = {
            "size": 8,
            "pitch": 1.25,
        }
        result = ThreadFieldHandler.serialize(value)
        assert result["standard"] == "metric"
        assert result["internal"] is False
        assert result["left_hand"] is False

    def test_serialize_string_metric_simple(self):
        """Test serializing metric string without pitch."""
        result = ThreadFieldHandler.serialize("M8")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25  # Coarse pitch

    def test_serialize_string_metric_with_pitch(self):
        """Test serializing metric string with pitch."""
        result = ThreadFieldHandler.serialize("M8x1.25")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25

    def test_serialize_string_metric_with_class(self):
        """Test serializing metric string with thread class."""
        result = ThreadFieldHandler.serialize("M8x1.25-6g")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25
        assert result["class"] == "6g"
        assert result["internal"] is False

    def test_serialize_string_metric_internal(self):
        """Test serializing metric internal thread string."""
        result = ThreadFieldHandler.serialize("M8x1.25-6H")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25
        assert result["class"] == "6h"
        assert result["internal"] is True

    def test_serialize_string_metric_left_hand(self):
        """Test serializing metric left-hand thread string."""
        result = ThreadFieldHandler.serialize("M8x1.25-6g LH")
        assert result["standard"] == "metric"
        assert result["left_hand"] is True

    def test_serialize_string_unc(self):
        """Test serializing UNC thread string."""
        result = ThreadFieldHandler.serialize("1/4-20 UNC")
        assert result["standard"] == "unc"
        assert result["size"] == 0.25
        assert result["tpi"] == 20

    def test_serialize_string_unc_with_class(self):
        """Test serializing UNC thread string with class."""
        result = ThreadFieldHandler.serialize("1/4-20 UNC-2A")
        assert result["standard"] == "unc"
        assert result["size"] == 0.25
        assert result["tpi"] == 20
        assert result["class"] == "2A"
        assert result["internal"] is False

    def test_serialize_string_unc_internal(self):
        """Test serializing UNC internal thread string."""
        result = ThreadFieldHandler.serialize("1/4-20 UNC-2B")
        assert result["standard"] == "unc"
        assert result["class"] == "2B"
        assert result["internal"] is True

    def test_serialize_string_unf(self):
        """Test serializing UNF thread string."""
        result = ThreadFieldHandler.serialize("1/4-28 UNF")
        assert result["standard"] == "unf"
        assert result["size"] == 0.25
        assert result["tpi"] == 28

    def test_serialize_string_unef(self):
        """Test serializing UNEF thread string."""
        result = ThreadFieldHandler.serialize("1/4-32 UNEF")
        assert result["standard"] == "unef"
        assert result["size"] == 0.25
        assert result["tpi"] == 32

    def test_serialize_string_case_insensitive(self):
        """Test serializing string is case insensitive."""
        result = ThreadFieldHandler.serialize("m8x1.25")
        assert result["standard"] == "metric"
        assert result["size"] == 8

    def test_serialize_invalid_string(self):
        """Test serializing invalid string returns None."""
        result = ThreadFieldHandler.serialize("invalid")
        assert result is None

    def test_serialize_invalid_type(self):
        """Test serializing invalid type returns None."""
        result = ThreadFieldHandler.serialize([1, 2, 3])
        assert result is None


class TestThreadDeserialization:
    """Tests for thread deserialization."""

    def test_deserialize_none(self):
        """Test deserializing None returns None."""
        result = ThreadFieldHandler.deserialize(None)
        assert result is None

    def test_deserialize_dict(self):
        """Test deserializing a dict returns it unchanged."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "class": "6g",
            "internal": False,
            "left_hand": False,
        }
        result = ThreadFieldHandler.deserialize(value)
        assert result == value

    def test_deserialize_fallback_to_serialize(self):
        """Test deserializing non-dict falls back to serialize."""
        result = ThreadFieldHandler.deserialize("M8x1.25")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25


class TestThreadValidation:
    """Tests for thread validation."""

    def test_validate_none(self):
        """Test validating None is allowed."""
        assert ThreadFieldHandler.validate(None) is True

    def test_validate_valid_metric_dict(self):
        """Test validating valid metric thread dict."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "class": "6g",
        }
        assert ThreadFieldHandler.validate(value) is True

    def test_validate_valid_metric_string(self):
        """Test validating valid metric thread string."""
        assert ThreadFieldHandler.validate("M8x1.25") is True

    def test_validate_valid_unc_dict(self):
        """Test validating valid UNC thread dict."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "2a",
        }
        assert ThreadFieldHandler.validate(value) is True

    def test_validate_valid_unc_string(self):
        """Test validating valid UNC thread string."""
        assert ThreadFieldHandler.validate("1/4-20 UNC") is True

    def test_validate_invalid_format(self):
        """Test validating invalid format raises error."""
        with pytest.raises(ValueError, match="Invalid thread format"):
            ThreadFieldHandler.validate("invalid")

    def test_validate_invalid_standard(self):
        """Test validating invalid standard raises error."""
        value = {
            "standard": "invalid",
            "size": 8,
            "pitch": 1.25,
        }
        with pytest.raises(ValueError, match="Invalid thread standard"):
            ThreadFieldHandler.validate(value)

    def test_validate_missing_size(self):
        """Test validating thread without size raises error."""
        value = {
            "standard": "metric",
            "pitch": 1.25,
        }
        with pytest.raises(ValueError, match="must have a size"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_size_too_small(self):
        """Test validating metric size below minimum raises error."""
        value = {
            "standard": "metric",
            "size": 0.1,
            "pitch": 0.1,
        }
        with pytest.raises(ValueError, match="outside valid range"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_size_too_large(self):
        """Test validating metric size above maximum raises error."""
        value = {
            "standard": "metric",
            "size": 100,
            "pitch": 6,
        }
        with pytest.raises(ValueError, match="outside valid range"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_default_coarse_pitch(self):
        """Test validation defaults to coarse pitch for standard sizes."""
        value = {
            "standard": "metric",
            "size": 8,
        }
        # Should not raise, defaults to coarse pitch
        assert ThreadFieldHandler.validate(value) is True

    def test_validate_metric_no_standard_coarse_pitch(self):
        """Test validation fails when no standard coarse pitch and pitch not specified."""
        value = {
            "standard": "metric",
            "size": 7.5,  # Non-standard size
        }
        with pytest.raises(ValueError, match="No standard coarse pitch"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_negative_pitch(self):
        """Test validating metric thread with negative pitch raises error."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": -1.25,
        }
        with pytest.raises(ValueError, match="must be positive"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_pitch_exceeds_size(self):
        """Test validating metric thread with pitch > size raises error."""
        value = {
            "standard": "metric",
            "size": 3,
            "pitch": 5,
        }
        with pytest.raises(ValueError, match="Invalid pitch"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_invalid_fine_pitch(self):
        """Test validating metric thread with invalid fine pitch raises error."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 0.5,  # Not a valid fine pitch for M8
        }
        with pytest.raises(ValueError, match="Invalid pitch"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_valid_fine_pitch(self):
        """Test validating metric thread with valid fine pitch."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.0,  # Valid fine pitch for M8
        }
        assert ThreadFieldHandler.validate(value) is True

    def test_validate_metric_invalid_thread_class(self):
        """Test validating metric thread with invalid class raises error."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "class": "2a",  # Unified class, not metric
        }
        with pytest.raises(ValueError, match="Invalid metric thread class"):
            ThreadFieldHandler.validate(value)

    def test_validate_metric_valid_thread_classes(self):
        """Test validating metric thread with all valid classes."""
        for thread_class in ["4h", "5h", "6h", "7h", "8h", "4g", "5g", "6g", "7g", "8g"]:
            value = {
                "standard": "metric",
                "size": 8,
                "pitch": 1.25,
                "class": thread_class,
            }
            assert ThreadFieldHandler.validate(value) is True

    def test_validate_unc_missing_tpi(self):
        """Test validating UNC thread without TPI raises error."""
        value = {
            "standard": "unc",
            "size": 0.25,
        }
        with pytest.raises(ValueError, match="require TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unc_non_standard_tpi(self):
        """Test validating UNC thread with non-standard TPI raises error."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 28,  # Standard is 20 for 1/4-20 UNC
        }
        with pytest.raises(ValueError, match="Non-standard TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unc_negative_tpi(self):
        """Test validating UNC thread with negative TPI raises error."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": -20,
        }
        with pytest.raises(ValueError, match="Non-standard TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unc_excessive_tpi(self):
        """Test validating UNC thread with excessive TPI raises error."""
        value = {
            "standard": "unc",
            "size": 2.0,
            "tpi": 100,
        }
        with pytest.raises(ValueError, match="Non-standard TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unc_invalid_thread_class(self):
        """Test validating UNC thread with invalid class raises error."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "6g",  # Metric class, not unified
        }
        with pytest.raises(ValueError, match="Invalid unified thread class"):
            ThreadFieldHandler.validate(value)

    def test_validate_unc_valid_thread_classes(self):
        """Test validating UNC thread with all valid classes."""
        for thread_class in ["1a", "2a", "3a", "1b", "2b", "3b"]:
            value = {
                "standard": "unc",
                "size": 0.25,
                "tpi": 20,
                "class": thread_class,
            }
            assert ThreadFieldHandler.validate(value) is True

    def test_validate_unf_missing_tpi(self):
        """Test validating UNF thread without TPI raises error."""
        value = {
            "standard": "unf",
            "size": 0.25,
        }
        with pytest.raises(ValueError, match="require TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unf_non_standard_tpi(self):
        """Test validating UNF thread with non-standard TPI raises error."""
        value = {
            "standard": "unf",
            "size": 0.25,
            "tpi": 20,  # Standard is 28 for 1/4-28 UNF
        }
        with pytest.raises(ValueError, match="Non-standard TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unef_missing_tpi(self):
        """Test validating UNEF thread without TPI raises error."""
        value = {
            "standard": "unef",
            "size": 0.25,
        }
        with pytest.raises(ValueError, match="require TPI"):
            ThreadFieldHandler.validate(value)

    def test_validate_unef_negative_tpi(self):
        """Test validating UNEF thread with negative TPI raises error."""
        value = {
            "standard": "unef",
            "size": 0.25,
            "tpi": -32,
        }
        with pytest.raises(ValueError, match="must be positive"):
            ThreadFieldHandler.validate(value)

    def test_validate_unef_excessive_tpi(self):
        """Test validating UNEF thread with excessive TPI raises error."""
        value = {
            "standard": "unef",
            "size": 0.25,
            "tpi": 40,
        }
        with pytest.raises(ValueError, match="unusually high"):
            ThreadFieldHandler.validate(value)


class TestThreadDefault:
    """Tests for thread default value."""

    def test_default(self):
        """Test default value is None."""
        result = ThreadFieldHandler.default()
        assert result is None


class TestThreadStringParsing:
    """Tests for parsing thread strings."""

    def test_parse_metric_simple(self):
        """Test parsing simple metric thread."""
        result = ThreadFieldHandler._parse_thread_string("M8")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25

    def test_parse_metric_with_pitch(self):
        """Test parsing metric thread with pitch."""
        result = ThreadFieldHandler._parse_thread_string("M8x1.25")
        assert result["standard"] == "metric"
        assert result["size"] == 8
        assert result["pitch"] == 1.25

    def test_parse_metric_with_class(self):
        """Test parsing metric thread with class."""
        result = ThreadFieldHandler._parse_thread_string("M8x1.25-6g")
        assert result["class"] == "6g"
        assert result["internal"] is False

    def test_parse_metric_internal_class(self):
        """Test parsing metric thread with internal class."""
        result = ThreadFieldHandler._parse_thread_string("M8x1.25-6H")
        assert result["class"] == "6h"
        assert result["internal"] is True

    def test_parse_metric_left_hand(self):
        """Test parsing metric left-hand thread."""
        result = ThreadFieldHandler._parse_thread_string("M8x1.25 LH")
        assert result["left_hand"] is True

    def test_parse_metric_fine_pitch(self):
        """Test parsing metric fine pitch thread."""
        result = ThreadFieldHandler._parse_thread_string("M8x1")
        assert result["size"] == 8
        assert result["pitch"] == 1.0

    def test_parse_unc_fractional(self):
        """Test parsing UNC thread with fractional size."""
        result = ThreadFieldHandler._parse_thread_string("1/4-20 UNC")
        assert result["standard"] == "unc"
        assert result["size"] == 0.25
        assert result["tpi"] == 20

    def test_parse_unc_with_class(self):
        """Test parsing UNC thread with class."""
        result = ThreadFieldHandler._parse_thread_string("1/4-20 UNC-2A")
        assert result["class"] == "2A"
        assert result["internal"] is False

    def test_parse_unc_internal_class(self):
        """Test parsing UNC thread with internal class."""
        result = ThreadFieldHandler._parse_thread_string("1/4-20 UNC-2B")
        assert result["class"] == "2B"
        assert result["internal"] is True

    def test_parse_unf(self):
        """Test parsing UNF thread."""
        result = ThreadFieldHandler._parse_thread_string("1/4-28 UNF")
        assert result["standard"] == "unf"
        assert result["size"] == 0.25
        assert result["tpi"] == 28

    def test_parse_unef(self):
        """Test parsing UNEF thread."""
        result = ThreadFieldHandler._parse_thread_string("1/4-32 UNEF")
        assert result["standard"] == "unef"
        assert result["tpi"] == 32

    def test_parse_unified_left_hand(self):
        """Test parsing unified left-hand thread."""
        result = ThreadFieldHandler._parse_thread_string("1/4-20 UNC LH")
        assert result["left_hand"] is True

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive."""
        result = ThreadFieldHandler._parse_thread_string("m8x1.25-6g")
        assert result["standard"] == "metric"

    def test_parse_invalid_string(self):
        """Test parsing invalid string returns None."""
        result = ThreadFieldHandler._parse_thread_string("invalid")
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = ThreadFieldHandler._parse_thread_string("")
        assert result is None


class TestThreadDisplayFormatting:
    """Tests for thread display formatting."""

    def test_format_display_none(self):
        """Test formatting None returns empty string."""
        result = ThreadFieldHandler.format_display(None)
        assert result == ""

    def test_format_display_metric_simple(self):
        """Test formatting simple metric thread."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "M8x1.25"

    def test_format_display_metric_with_class(self):
        """Test formatting metric thread with class."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "class": "6g",
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "M8x1.25-6g"

    def test_format_display_metric_left_hand(self):
        """Test formatting metric left-hand thread."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "left_hand": True,
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "M8x1.25 LH"

    def test_format_display_unc_fractional(self):
        """Test formatting UNC thread with fractional size."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "1/4-20 UNC"

    def test_format_display_unc_with_class(self):
        """Test formatting UNC thread with class."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "2A",
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "1/4-20 UNC-2A"

    def test_format_display_unc_left_hand(self):
        """Test formatting UNC left-hand thread."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "left_hand": True,
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "1/4-20 UNC LH"

    def test_format_display_unf(self):
        """Test formatting UNF thread."""
        value = {
            "standard": "unf",
            "size": 0.25,
            "tpi": 28,
        }
        result = ThreadFieldHandler.format_display(value)
        assert result == "1/4-28 UNF"

    def test_format_display_fractional_sizes(self):
        """Test formatting various fractional sizes."""
        test_cases = [
            (0.25, "1/4"),
            (0.3125, "5/16"),
            (0.375, "3/8"),
            (0.5, "1/2"),
            (0.625, "5/8"),
            (0.75, "3/4"),
        ]
        for size, expected in test_cases:
            value = {
                "standard": "unc",
                "size": size,
                "tpi": 20,
            }
            result = ThreadFieldHandler.format_display(value)
            assert expected in result

    def test_format_display_invalid_value(self):
        """Test formatting invalid value returns string representation."""
        result = ThreadFieldHandler.format_display("invalid")
        assert result == "invalid"


class TestThreadHelperMethods:
    """Tests for thread helper methods."""

    def test_get_coarse_pitch_standard_size(self):
        """Test getting coarse pitch for standard sizes."""
        assert ThreadFieldHandler.get_coarse_pitch(8) == 1.25
        assert ThreadFieldHandler.get_coarse_pitch(10) == 1.5
        assert ThreadFieldHandler.get_coarse_pitch(12) == 1.75

    def test_get_coarse_pitch_non_standard_size(self):
        """Test getting coarse pitch for non-standard size returns None."""
        result = ThreadFieldHandler.get_coarse_pitch(7.5)
        assert result is None

    def test_pitch_to_tpi(self):
        """Test converting pitch to TPI."""
        # 1.25mm pitch = 20.32 TPI
        result = ThreadFieldHandler.pitch_to_tpi(1.25)
        assert result == pytest.approx(20.32, rel=0.01)

    def test_pitch_to_tpi_zero(self):
        """Test converting zero pitch raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            ThreadFieldHandler.pitch_to_tpi(0)

    def test_pitch_to_tpi_negative(self):
        """Test converting negative pitch raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            ThreadFieldHandler.pitch_to_tpi(-1.25)

    def test_tpi_to_pitch(self):
        """Test converting TPI to pitch."""
        # 20 TPI = 1.27mm pitch
        result = ThreadFieldHandler.tpi_to_pitch(20)
        assert result == pytest.approx(1.27, rel=0.01)

    def test_tpi_to_pitch_zero(self):
        """Test converting zero TPI raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            ThreadFieldHandler.tpi_to_pitch(0)

    def test_tpi_to_pitch_negative(self):
        """Test converting negative TPI raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            ThreadFieldHandler.tpi_to_pitch(-20)


class TestThreadMetricToImperialConversion:
    """Tests for converting metric threads to imperial."""

    def test_convert_to_imperial_none(self):
        """Test converting None returns None."""
        result = ThreadFieldHandler.convert_to_imperial(None)
        assert result is None

    def test_convert_to_imperial_already_imperial(self):
        """Test converting imperial thread returns None."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result is None

    def test_convert_to_imperial_m6_to_quarter_inch(self):
        """Test converting M6 to approximate 1/4-20 UNC."""
        value = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["standard"] == "unc"
        assert result["size"] == pytest.approx(0.25, rel=0.1)
        assert result["tpi"] == 20

    def test_convert_to_imperial_m8_fine(self):
        """Test converting M8 fine pitch to UNF equivalent."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.0,  # Fine pitch
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["standard"] == "unf"

    def test_convert_to_imperial_with_thread_class(self):
        """Test converting metric thread class to unified."""
        value = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
            "class": "6g",
            "internal": False,
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["class"] == "2a"

    def test_convert_to_imperial_internal_thread(self):
        """Test converting metric internal thread."""
        value = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
            "class": "6h",
            "internal": True,
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["class"] == "2b"

    def test_convert_to_imperial_loose_fit_class(self):
        """Test converting metric loose fit class."""
        value = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
            "class": "4g",
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["class"] == "1a"

    def test_convert_to_imperial_tight_fit_class(self):
        """Test converting metric tight fit class."""
        value = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
            "class": "5g",
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["class"] == "3a"

    def test_convert_to_imperial_left_hand(self):
        """Test converting left-hand thread preserves handedness."""
        value = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
            "left_hand": True,
        }
        result = ThreadFieldHandler.convert_to_imperial(value)
        assert result["left_hand"] is True


class TestThreadImperialToMetricConversion:
    """Tests for converting imperial threads to metric."""

    def test_convert_to_metric_none(self):
        """Test converting None returns None."""
        result = ThreadFieldHandler.convert_to_metric(None)
        assert result is None

    def test_convert_to_metric_already_metric(self):
        """Test converting metric thread returns None."""
        value = {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result is None

    def test_convert_to_metric_quarter_inch_to_m6(self):
        """Test converting 1/4-20 UNC to approximate M6."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["standard"] == "metric"
        assert result["size"] == 6
        assert result["pitch"] == pytest.approx(1.0, rel=0.2)

    def test_convert_to_metric_with_thread_class(self):
        """Test converting unified thread class to metric."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "2a",
            "internal": False,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["class"] == "6g"

    def test_convert_to_metric_internal_thread(self):
        """Test converting unified internal thread."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "2b",
            "internal": True,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["class"] == "6h"

    def test_convert_to_metric_loose_fit_class(self):
        """Test converting unified loose fit class."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "1a",
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["class"] == "4g"

    def test_convert_to_metric_tight_fit_class(self):
        """Test converting unified tight fit class."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "3a",
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["class"] == "5g"

    def test_convert_to_metric_left_hand(self):
        """Test converting left-hand thread preserves handedness."""
        value = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "left_hand": True,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["left_hand"] is True

    def test_convert_to_metric_unf(self):
        """Test converting UNF thread to metric."""
        value = {
            "standard": "unf",
            "size": 0.25,
            "tpi": 28,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["standard"] == "metric"
        assert result["size"] in ThreadFieldHandler.METRIC_SIZE_RANGE["common"]

    def test_convert_to_metric_unef(self):
        """Test converting UNEF thread to metric."""
        value = {
            "standard": "unef",
            "size": 0.25,
            "tpi": 32,
        }
        result = ThreadFieldHandler.convert_to_metric(value)
        assert result["standard"] == "metric"


class TestThreadRoundTripConversions:
    """Tests for round-trip conversions between metric and imperial."""

    def test_round_trip_metric_to_imperial_to_metric(self):
        """Test converting metric to imperial and back."""
        original = {
            "standard": "metric",
            "size": 6,
            "pitch": 1,
            "class": "6g",
        }
        imperial = ThreadFieldHandler.convert_to_imperial(original)
        metric = ThreadFieldHandler.convert_to_metric(imperial)

        # Should be close to original
        assert metric["standard"] == "metric"
        assert metric["size"] == pytest.approx(original["size"], rel=0.1)

    def test_round_trip_imperial_to_metric_to_imperial(self):
        """Test converting imperial to metric and back."""
        original = {
            "standard": "unc",
            "size": 0.25,
            "tpi": 20,
            "class": "2a",
        }
        metric = ThreadFieldHandler.convert_to_metric(original)
        imperial = ThreadFieldHandler.convert_to_imperial(metric)

        # Should be close to original
        assert imperial["standard"] in ("unc", "unf")
        assert imperial["size"] == pytest.approx(original["size"], rel=0.1)
