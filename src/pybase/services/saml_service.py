"""
SAML 2.0 service for Single Sign-On authentication.

Handles SAML authentication flow including request generation,
response processing, and attribute extraction from Identity Providers.
"""

import base64
import hashlib
import json
import secrets
import zlib
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import BaseModel

from pybase.core.config import settings
from pybase.core.security import create_token_pair, generate_random_string


# =============================================================================
# SAML Data Models
# =============================================================================


class SAMLAuthRequest(BaseModel):
    """SAML authentication request data."""

    id: str  # Request ID
    saml_request: str  # Base64-encoded SAML request
    relay_state: str  # State parameter for CSRF protection
    issue_instant: datetime  # When request was issued
    destination_url: str  # IdP SSO URL


class SAMLResponse(BaseModel):
    """SAML authentication response data."""

    name_id: str  # User's NameID from IdP
    attributes: dict[str, Any]  # SAML attributes
    issuer: str  # IdP entity ID
    session_index: str | None = None  # SAML session index
    assertion_id: str | None = None  # Assertion ID for logout


class SAMLUserAttributes(BaseModel):
    """Extracted user attributes from SAML response."""

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None


# =============================================================================
# SAML Service
# =============================================================================


class SAMLService:
    """
    SAML 2.0 authentication service.

    Handles SAML authentication flow with Identity Providers.
    Supports SAML 2.0 Web Browser SSO Profile.
    """

    # SAML protocol constants
    SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
    SAMLP_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
    SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"

    # NameID formats
    NAMEID_FORMAT_EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    NAMEID_FORMAT_UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
    NAMEID_FORMAT_PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
    NAMEID_FORMAT_TRANSIENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"

    def __init__(
        self,
        sp_entity_id: str | None = None,
        sp_acs_url: str | None = None,
        sp_slo_url: str | None = None,
        idp_sso_url: str | None = None,
        idp_slo_url: str | None = None,
        idp_entity_id: str | None = None,
        idp_cert: str | None = None,
        name_id_format: str = NAMEID_FORMAT_EMAIL,
        attribute_mapping: dict[str, str] | None = None,
        role_mapping: dict[str, list[str]] | None = None,
        group_attribute: str = "groups",
    ):
        """
        Initialize SAML service with configuration.

        Args:
            sp_entity_id: Service Provider entity ID
            sp_acs_url: Assertion Consumer Service URL
            sp_slo_url: Single Logout Service URL (optional)
            idp_sso_url: Identity Provider SSO URL
            idp_slo_url: Identity Provider SLO URL (optional)
            idp_entity_id: Identity Provider entity ID
            idp_cert: Identity Provider X.509 certificate (PEM format)
            name_id_format: SAML NameID format
            attribute_mapping: SAML attributes to user field mapping
            role_mapping: SAML groups to user roles mapping
            group_attribute: SAML attribute name for groups
        """
        self.sp_entity_id = sp_entity_id or settings.saml_sp_entity_id
        self.sp_acs_url = sp_acs_url or (settings.saml_sp_acs_url or f"{settings.api_v1_prefix}/saml/acs")
        self.sp_slo_url = sp_slo_url or settings.saml_sp_slo_url
        self.idp_sso_url = idp_sso_url or settings.saml_idp_sso_url
        self.idp_slo_url = idp_slo_url or settings.saml_idp_slo_url
        self.idp_entity_id = idp_entity_id
        self.idp_cert = idp_cert
        self.name_id_format = name_id_format
        self.attribute_mapping = attribute_mapping or settings.saml_attribute_mapping
        self.role_mapping = role_mapping or {}
        self.group_attribute = group_attribute

    # =========================================================================
    # SAML Request Generation
    # =========================================================================

    def generate_auth_request(
        self,
        relay_state: str | None = None,
        force_authn: bool = False,
        name_id_policy: str | None = None,
    ) -> SAMLAuthRequest:
        """
        Generate a SAML 2.0 authentication request.

        Args:
            relay_state: State parameter for CSRF protection
            force_authn: Force re-authentication at IdP
            name_id_policy: Override NameID policy format

        Returns:
            SAMLAuthRequest with encoded SAML request and relay state

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.idp_sso_url:
            raise ValueError("IdP SSO URL is required")

        if not self.sp_entity_id:
            raise ValueError("SP entity ID is required")

        if not self.sp_acs_url:
            raise ValueError("SP ACS URL is required")

        # Generate request ID and timestamp
        request_id = f"_id-{generate_random_string(16)}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Use provided NameID format or default
        name_id_format = name_id_policy or self.name_id_format

        # Build SAML auth request XML
        saml_request = self._build_auth_request_xml(
            request_id=request_id,
            issue_instant=issue_instant,
            name_id_format=name_id_format,
            force_authn=force_authn,
        )

        # Deflate and encode the request
        encoded_request = self._encode_saml_request(saml_request)

        # Generate relay state if not provided
        if not relay_state:
            relay_state = generate_random_string(32)

        return SAMLAuthRequest(
            id=request_id,
            saml_request=encoded_request,
            relay_state=relay_state,
            issue_instant=datetime.now(timezone.utc),
            destination_url=self.idp_sso_url,
        )

    def _build_auth_request_xml(
        self,
        request_id: str,
        issue_instant: str,
        name_id_format: str,
        force_authn: bool = False,
    ) -> str:
        """
        Build SAML authentication request XML.

        Args:
            request_id: Unique request ID
            issue_instant: ISO 8601 timestamp
            name_id_format: SAML NameID format
            force_authn: Whether to force authentication

        Returns:
            SAML auth request XML string
        """
        # Build root element
        root = ET.Element("samlp:AuthnRequest")
        root.set("xmlns:samlp", self.SAMLP_NS)
        root.set("xmlns:saml", self.SAML_NS)
        root.set("ID", request_id)
        root.set("Version", "2.0")
        root.set("IssueInstant", issue_instant)
        root.set("ProtocolBinding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST")
        root.set("AssertionConsumerServiceURL", self.sp_acs_url)
        root.set("Destination", self.idp_sso_url)

        if force_authn:
            root.set("ForceAuthn", "true")

        # Add Issuer
        issuer = ET.SubElement(root, "saml:Issuer")
        issuer.text = self.sp_entity_id

        # Add NameIDPolicy
        name_id_policy = ET.SubElement(root, "samlp:NameIDPolicy")
        name_id_policy.set("Format", name_id_format)
        name_id_policy.set("AllowCreate", "true")

        # Add RequestedAuthnContext
        authn_context = ET.SubElement(root, "samlp:RequestedAuthnContext")
        authn_context.set("Comparison", "exact")

        authn_context_class_ref = ET.SubElement(authn_context, "saml:AuthnContextClassRef")
        authn_context_class_ref.text = (
            "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
        )

        return ET.tostring(root, encoding="unicode")

    def _encode_saml_request(self, saml_request: str) -> str:
        """
        Encode SAML request using Deflate and Base64.

        Args:
            saml_request: SAML request XML string

        Returns:
            Deflated and Base64-encoded request
        """
        # Compress with deflate
        compressed = zlib.compress(saml_request.encode("utf-8"))[2:-4]

        # Base64 encode
        encoded = base64.b64encode(compressed).decode("utf-8")

        return encoded

    # =========================================================================
    # SAML Response Processing
    # =========================================================================

    def decode_saml_response(self, saml_response: str) -> SAMLResponse:
        """
        Decode and validate SAML response from IdP.

        Args:
            saml_response: Base64-encoded SAML response

        Returns:
            Parsed SAML response with user attributes

        Raises:
            ValueError: If response is invalid or missing required data
        """
        try:
            # Decode Base64
            decoded = base64.b64decode(saml_response)

            # Try to decompress if compressed
            try:
                xml_str = zlib.decompress(decoded, -15).decode("utf-8")
            except zlib.error:
                xml_str = decoded.decode("utf-8")

            # Parse XML
            root = ET.fromstring(xml_str)

            # Extract assertion data
            name_id = self._extract_name_id(root)
            issuer = self._extract_issuer(root)
            attributes = self._extract_attributes(root)
            session_index = self._extract_session_index(root)
            assertion_id = self._extract_assertion_id(root)

            return SAMLResponse(
                name_id=name_id,
                attributes=attributes,
                issuer=issuer,
                session_index=session_index,
                assertion_id=assertion_id,
            )

        except Exception as e:
            raise ValueError(f"Failed to decode SAML response: {e}") from e

    def _extract_name_id(self, root: ET.Element) -> str:
        """Extract NameID from SAML response."""
        # Try to find NameID in assertion
        name_id_elem = root.find(
            ".//saml:NameID",
            {"saml": self.SAML_NS},
        )

        if name_id_elem is None or not name_id_elem.text:
            raise ValueError("SAML response missing NameID")

        return name_id_elem.text.strip()

    def _extract_issuer(self, root: ET.Element) -> str:
        """Extract issuer from SAML response."""
        issuer_elem = root.find(
            ".//saml:Issuer",
            {"saml": self.SAML_NS},
        )

        if issuer_elem is None or not issuer_elem.text:
            raise ValueError("SAML response missing Issuer")

        return issuer_elem.text.strip()

    def _extract_attributes(self, root: ET.Element) -> dict[str, Any]:
        """Extract attributes from SAML assertion."""
        attributes: dict[str, Any] = {}

        # Find AttributeStatement
        attr_statement = root.find(
            ".//saml:AttributeStatement",
            {"saml": self.SAML_NS},
        )

        if attr_statement is None:
            return attributes

        # Extract all attributes
        for attr_elem in attr_statement.findall("saml:Attribute", {"saml": self.SAML_NS}):
            name = attr_elem.get("Name", "")
            if not name:
                continue

            # Extract attribute values
            values = []
            for value_elem in attr_elem.findall("saml:AttributeValue", {"saml": self.SAML_NS}):
                if value_elem.text:
                    values.append(value_elem.text.strip())

            # Store single value or list
            if len(values) == 1:
                attributes[name] = values[0]
            elif len(values) > 1:
                attributes[name] = values

        return attributes

    def _extract_session_index(self, root: ET.Element) -> str | None:
        """Extract session index from SAML response."""
        session_index = root.find(
            ".//samlp:SessionIndex",
            {"samlp": self.SAMLP_NS},
        )

        return session_index.text if session_index is not None else None

    def _extract_assertion_id(self, root: ET.Element) -> str | None:
        """Extract assertion ID from SAML response."""
        assertion = root.find(
            ".//saml:Assertion",
            {"saml": self.SAML_NS},
        )

        return assertion.get("ID") if assertion is not None else None

    # =========================================================================
    # User Attribute Mapping
    # =========================================================================

    def map_user_attributes(self, saml_attributes: dict[str, Any]) -> SAMLUserAttributes:
        """
        Map SAML attributes to user profile fields.

        Args:
            saml_attributes: Raw SAML attributes from IdP

        Returns:
            Mapped user attributes
        """
        user_attrs = SAMLUserAttributes()

        # Map attributes using configured mapping
        for field, saml_attr in self.attribute_mapping.items():
            if saml_attr in saml_attributes:
                value = saml_attributes[saml_attr]

                if field == "email":
                    user_attrs.email = str(value) if value else None
                elif field == "first_name":
                    user_attrs.first_name = str(value) if value else None
                elif field == "last_name":
                    user_attrs.last_name = str(value) if value else None
                elif field == "name":
                    user_attrs.display_name = str(value) if value else None
                elif field in ("roles", "groups"):
                    if isinstance(value, list):
                        if field == "roles":
                            user_attrs.roles = value
                        else:
                            user_attrs.groups = value
                    elif isinstance(value, str):
                        parsed_list = [v.strip() for v in value.split(",") if v.strip()]
                        if field == "roles":
                            user_attrs.roles = parsed_list
                        else:
                            user_attrs.groups = parsed_list

        # Extract groups from group_attribute if not already set
        if not user_attrs.groups and self.group_attribute in saml_attributes:
            groups_value = saml_attributes[self.group_attribute]
            if isinstance(groups_value, list):
                user_attrs.groups = groups_value
            elif isinstance(groups_value, str):
                user_attrs.groups = [g.strip() for g in groups_value.split(",") if g.strip()]

        return user_attrs

    def map_user_roles(self, saml_groups: list[str] | None) -> list[str]:
        """
        Map SAML groups to user roles.

        Args:
            saml_groups: List of groups from SAML attributes

        Returns:
            List of user roles
        """
        if not saml_groups or not self.role_mapping:
            return []

        roles: set[str] = set()

        for group in saml_groups:
            if group in self.role_mapping:
                roles.update(self.role_mapping[group])

        return list(roles)

    # =========================================================================
    # SAML Metadata Generation
    # =========================================================================

    def generate_sp_metadata(self) -> str:
        """
        Generate SAML 2.0 Service Provider metadata XML.

        Returns:
            SP metadata XML string

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.sp_entity_id:
            raise ValueError("SP entity ID is required")

        if not self.sp_acs_url:
            raise ValueError("SP ACS URL is required")

        # Build metadata XML
        root = ET.Element("md:EntityDescriptor")
        root.set("xmlns:md", "urn:oasis:names:tc:SAML:2.0:metadata")
        root.set("xmlns:ds", "http://www.w3.org/2000/09/xmldsig#")
        root.set("xmlns:saml", "urn:oasis:names:tc:SAML:2.0:assertion")
        root.set("entityID", self.sp_entity_id)

        # Add SP SSO descriptor
        sp_sso_desc = ET.SubElement(root, "md:SPSSODescriptor")
        sp_sso_desc.set("protocolSupportEnumeration", "urn:oasis:names:tc:SAML:2.0:protocol")
        sp_sso_desc.set("AuthnRequestsSigned", "false")
        sp_sso_desc.set("WantAssertionsSigned", "true")

        # Add NameID formats
        for name_id_format in [
            self.NAMEID_FORMAT_UNSPECIFIED,
            self.NAMEID_FORMAT_EMAIL,
            self.NAMEID_FORMAT_TRANSIENT,
            self.NAMEID_FORMAT_PERSISTENT,
        ]:
            name_id_elem = ET.SubElement(sp_sso_desc, "md:NameIDFormat")
            name_id_elem.text = name_id_format

        # Add Assertion Consumer Service
        acs_service = ET.SubElement(sp_sso_desc, "md:AssertionConsumerService")
        acs_service.set("Binding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST")
        acs_service.set("Location", self.sp_acs_url)
        acs_service.set("index", "0")

        # Add Single Logout Service if configured
        if self.sp_slo_url:
            slo_service = ET.SubElement(sp_sso_desc, "md:SingleLogoutService")
            slo_service.set("Binding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect")
            slo_service.set("Location", self.sp_slo_url)

        return ET.tostring(root, encoding="unicode")

    # =========================================================================
    # Utility Functions
    # =========================================================================

    def generate_relay_state(self) -> str:
        """
        Generate a secure relay state parameter.

        Returns:
            Random relay state string
        """
        return generate_random_string(32)

    def validate_relay_state(self, relay_state: str, stored_state: str) -> bool:
        """
        Validate relay state parameter.

        Args:
            relay_state: Relay state from callback
            stored_state: Stored relay state from request

        Returns:
            True if relay state is valid
        """
        return relay_state == stored_state

    @staticmethod
    def get_user_id_from_attributes(attributes: SAMLUserAttributes) -> str:
        """
        Generate a stable user ID from SAML attributes.

        Args:
            attributes: Mapped user attributes

        Returns:
            User ID string
        """
        if attributes.email:
            return f"saml:{attributes.email}"
        else:
            # Fallback: hash of all attributes
            attrs_str = json.dumps(attributes.model_dump(), sort_keys=True)
            hash_val = hashlib.sha256(attrs_str.encode()).hexdigest()[:16]
            return f"saml:{hash_val}"


# =============================================================================
# Convenience Functions
# =============================================================================


def create_saml_service(saml_config: Any | None = None) -> SAMLService:
    """
    Create a SAML service instance from configuration.

    Args:
        saml_config: SAMLConfig model or dict with SAML settings

    Returns:
        Configured SAML service instance
    """
    if saml_config is None:
        # Use default configuration from settings
        return SAMLService()

    # Extract configuration from SAMLConfig model or dict
    if hasattr(saml_config, "sp_entity_id"):
        # SAMLConfig model
        config_dict = {
            "sp_entity_id": saml_config.sp_entity_id,
            "sp_acs_url": saml_config.sp_acs_url,
            "sp_slo_url": saml_config.sp_slo_url,
            "idp_sso_url": saml_config.idp_sso_url,
            "idp_slo_url": saml_config.idp_slo_url,
            "idp_entity_id": saml_config.idp_entity_id,
            "idp_cert": saml_config.idp_x509_cert,
            "name_id_format": saml_config.name_id_format,
            "attribute_mapping": json.loads(saml_config.attribute_mapping) if saml_config.attribute_mapping else None,
            "role_mapping": json.loads(saml_config.role_mapping) if saml_config.role_mapping else None,
            "group_attribute": saml_config.group_attribute,
        }
    else:
        # Dict-like configuration
        config_dict = dict(saml_config)

    return SAMLService(**config_dict)
