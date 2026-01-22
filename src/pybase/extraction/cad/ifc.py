"""IFC (Industry Foundation Classes) file parser for PyBase.

Uses ifcopenshell library to extract information from BIM files:
- Building elements (walls, doors, windows, slabs, etc.)
- Properties and property sets
- Spatial hierarchy (site, building, storey, space)
- Relationships between elements
- Material information
- Quantities
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pybase.extraction.base import (
    CADExtractionResult,
    ExtractedDimension,
    ExtractedEntity,
    ExtractedLayer,
    ExtractedText,
    GeometrySummary,
)

logger = logging.getLogger(__name__)

# Try to import ifcopenshell
try:
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.pset

    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False
    ifcopenshell = None  # type: ignore


@dataclass
class IFCElement:
    """Represents an extracted IFC element."""

    global_id: str
    ifc_class: str
    name: str | None = None
    description: str | None = None
    object_type: str | None = None
    storey: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    quantities: dict[str, Any] = field(default_factory=dict)
    materials: list[str] = field(default_factory=list)
    bbox: tuple[float, float, float, float, float, float] | None = None  # min/max x,y,z

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_id": self.global_id,
            "ifc_class": self.ifc_class,
            "name": self.name,
            "description": self.description,
            "object_type": self.object_type,
            "storey": self.storey,
            "properties": self.properties,
            "quantities": self.quantities,
            "materials": self.materials,
            "bbox": self.bbox,
        }


@dataclass
class IFCSpatialStructure:
    """Represents the spatial hierarchy of an IFC model."""

    project: str | None = None
    sites: list[dict[str, Any]] = field(default_factory=list)
    buildings: list[dict[str, Any]] = field(default_factory=list)
    storeys: list[dict[str, Any]] = field(default_factory=list)
    spaces: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "sites": self.sites,
            "buildings": self.buildings,
            "storeys": self.storeys,
            "spaces": self.spaces,
        }


@dataclass
class IFCExtractionResult(CADExtractionResult):
    """Extended result for IFC extraction."""

    elements: list[IFCElement] = field(default_factory=list)
    spatial_structure: IFCSpatialStructure | None = None
    element_counts: dict[str, int] = field(default_factory=dict)
    property_sets: list[dict[str, Any]] = field(default_factory=list)
    type_objects: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "elements": [e.to_dict() for e in self.elements],
                "spatial_structure": self.spatial_structure.to_dict()
                if self.spatial_structure
                else None,
                "element_counts": self.element_counts,
                "property_sets": self.property_sets,
                "type_objects": self.type_objects,
            }
        )
        return base


class IFCParser:
    """Parser for IFC (Industry Foundation Classes) BIM files.

    Extracts building elements, properties, spatial structure, and relationships
    from IFC files.

    Example:
        parser = IFCParser()
        result = parser.parse("building.ifc")

        # Access elements
        for elem in result.elements:
            print(f"{elem.ifc_class}: {elem.name}")

        # Access spatial structure
        print(f"Storeys: {len(result.spatial_structure.storeys)}")
    """

    # Common IFC element types to extract
    ELEMENT_TYPES: list[str] = [
        "IfcWall",
        "IfcWallStandardCase",
        "IfcDoor",
        "IfcWindow",
        "IfcSlab",
        "IfcRoof",
        "IfcBeam",
        "IfcColumn",
        "IfcStair",
        "IfcRamp",
        "IfcRailing",
        "IfcCurtainWall",
        "IfcPlate",
        "IfcMember",
        "IfcPile",
        "IfcFooting",
        "IfcCovering",
        "IfcBuildingElementProxy",
        "IfcFurnishingElement",
        "IfcFlowTerminal",
        "IfcFlowSegment",
        "IfcFlowFitting",
        "IfcDistributionElement",
        "IfcOpeningElement",
    ]

    def __init__(
        self,
        extract_properties: bool = True,
        extract_quantities: bool = True,
        extract_materials: bool = True,
        max_elements: int = 50000,
    ):
        """Initialize the IFC parser.

        Args:
            extract_properties: Whether to extract property sets.
            extract_quantities: Whether to extract quantity sets.
            extract_materials: Whether to extract material information.
            max_elements: Maximum number of elements to extract.
        """
        self.extract_properties = extract_properties
        self.extract_quantities = extract_quantities
        self.extract_materials = extract_materials
        self.max_elements = max_elements

        if not IFCOPENSHELL_AVAILABLE:
            raise ImportError(
                "ifcopenshell is required for IFC parsing. Install with: pip install ifcopenshell"
            )

    def parse(self, source: str | Path) -> IFCExtractionResult:
        """Parse an IFC file and extract information.

        Args:
            source: File path to the IFC file.

        Returns:
            IFCExtractionResult with extracted elements, spatial structure, etc.
        """
        source_file = str(source)

        result = IFCExtractionResult(
            source_file=source_file,
            source_type="ifc",
        )

        try:
            # Open the IFC file
            ifc_file = ifcopenshell.open(str(source))

            # Extract metadata
            result.metadata = self._extract_metadata(ifc_file)

            # Extract spatial structure
            result.spatial_structure = self._extract_spatial_structure(ifc_file)

            # Extract element counts
            result.element_counts = self._count_elements(ifc_file)

            # Extract elements
            result.elements = self._extract_elements(ifc_file)

            # Convert elements to layers (by IFC class)
            result.layers = self._elements_to_layers(result.element_counts)

            # Extract geometry summary
            result.geometry_summary = self._extract_geometry_summary(ifc_file)

            # Extract property set definitions
            if self.extract_properties:
                result.property_sets = self._extract_property_set_definitions(ifc_file)

            # Extract type objects
            result.type_objects = self._extract_type_objects(ifc_file)

            # Add total counts to metadata for accuracy validation
            result.metadata["total_elements"] = len(result.elements)
            result.metadata["total_spatial"] = (
                len(result.spatial_structure.sites)
                + len(result.spatial_structure.buildings)
                + len(result.spatial_structure.storeys)
                + len(result.spatial_structure.spaces)
            )

        except Exception as e:
            result.errors.append(f"IFC parsing error: {e}")
            logger.exception("Error parsing IFC: %s", source_file)

        return result

    def _extract_metadata(self, ifc_file: Any) -> dict[str, Any]:
        """Extract file metadata."""
        metadata: dict[str, Any] = {}

        try:
            # Schema version
            metadata["schema"] = ifc_file.schema

            # Header info
            if hasattr(ifc_file, "header"):
                header = ifc_file.header
                if hasattr(header, "file_description"):
                    metadata["description"] = str(header.file_description)
                if hasattr(header, "file_name"):
                    fn = header.file_name
                    if hasattr(fn, "name"):
                        metadata["file_name"] = fn.name
                    if hasattr(fn, "author"):
                        metadata["author"] = fn.author
                    if hasattr(fn, "organization"):
                        metadata["organization"] = fn.organization
                    if hasattr(fn, "time_stamp"):
                        metadata["timestamp"] = fn.time_stamp
                    if hasattr(fn, "authorization"):
                        metadata["authorization"] = fn.authorization
                    if hasattr(fn, "preprocessor_version"):
                        metadata["preprocessor_version"] = fn.preprocessor_version
                    if hasattr(fn, "originating_system"):
                        metadata["originating_system"] = fn.originating_system

            # Project info
            projects = ifc_file.by_type("IfcProject")
            if projects and projects[0]:
                project = projects[0]
                metadata["project_name"] = getattr(project, "Name", None)
                metadata["project_description"] = getattr(project, "Description", None)

                # Units
                units_context = getattr(project, "UnitsInContext", None)
                if units_context:
                    try:
                        units = {}
                        for unit in getattr(units_context, "Units", []) or []:
                            try:
                                if hasattr(unit, "UnitType"):
                                    unit_name = str(unit.UnitType)
                                    if hasattr(unit, "Name"):
                                        units[unit_name] = unit.Name
                                    elif hasattr(unit, "Prefix") and hasattr(unit, "Name"):
                                        units[unit_name] = f"{unit.Prefix}{unit.Name}"
                            except Exception as e:
                                logger.debug("Error extracting unit: %s", e)
                        if units:
                            metadata["units"] = units
                    except Exception as e:
                        logger.debug("Error extracting units: %s", e)

        except Exception as e:
            logger.warning("Error extracting IFC metadata: %s", e)

        return metadata

    def _extract_spatial_structure(self, ifc_file: Any) -> IFCSpatialStructure:
        """Extract the spatial hierarchy."""
        structure = IFCSpatialStructure()

        try:
            # Project
            projects = ifc_file.by_type("IfcProject")
            if projects and projects[0]:
                structure.project = getattr(projects[0], "Name", None)

            # Sites
            for site in ifc_file.by_type("IfcSite"):
                try:
                    if hasattr(site, "GlobalId") and site.GlobalId:
                        structure.sites.append(
                            {
                                "global_id": site.GlobalId,
                                "name": getattr(site, "Name", None),
                                "description": getattr(site, "Description", None),
                            }
                        )
                except Exception as e:
                    logger.debug("Error extracting site: %s", e)

            # Buildings
            for building in ifc_file.by_type("IfcBuilding"):
                try:
                    if hasattr(building, "GlobalId") and building.GlobalId:
                        structure.buildings.append(
                            {
                                "global_id": building.GlobalId,
                                "name": getattr(building, "Name", None),
                                "description": getattr(building, "Description", None),
                                "elevation": getattr(building, "ElevationOfRefHeight", None),
                            }
                        )
                except Exception as e:
                    logger.debug("Error extracting building: %s", e)

            # Storeys
            for storey in ifc_file.by_type("IfcBuildingStorey"):
                try:
                    if hasattr(storey, "GlobalId") and storey.GlobalId:
                        structure.storeys.append(
                            {
                                "global_id": storey.GlobalId,
                                "name": getattr(storey, "Name", None),
                                "description": getattr(storey, "Description", None),
                                "elevation": getattr(storey, "Elevation", None),
                            }
                        )
                except Exception as e:
                    logger.debug("Error extracting storey: %s", e)

            # Spaces
            for space in ifc_file.by_type("IfcSpace"):
                try:
                    if hasattr(space, "GlobalId") and space.GlobalId:
                        structure.spaces.append(
                            {
                                "global_id": space.GlobalId,
                                "name": getattr(space, "Name", None),
                                "description": getattr(space, "Description", None),
                                "long_name": getattr(space, "LongName", None),
                            }
                        )
                except Exception as e:
                    logger.debug("Error extracting space: %s", e)

        except Exception as e:
            logger.warning("Error extracting spatial structure: %s", e)

        return structure

    def _count_elements(self, ifc_file: Any) -> dict[str, int]:
        """Count elements by IFC class."""
        counts: dict[str, int] = {}

        try:
            for element_type in self.ELEMENT_TYPES:
                try:
                    elements = ifc_file.by_type(element_type)
                    if elements:
                        counts[element_type] = len(elements)
                except RuntimeError:
                    # Type not in schema
                    pass

        except Exception as e:
            logger.warning("Error counting elements: %s", e)

        return counts

    def _extract_elements(self, ifc_file: Any) -> list[IFCElement]:
        """Extract building elements with their properties."""
        elements: list[IFCElement] = []
        count = 0

        try:
            # Build storey mapping
            storey_map = self._build_storey_map(ifc_file)

            for element_type in self.ELEMENT_TYPES:
                if count >= self.max_elements:
                    break

                try:
                    for element in ifc_file.by_type(element_type):
                        if count >= self.max_elements:
                            break

                        try:
                            # Extract element with individual error handling
                            # This prevents one bad element from failing the entire extraction

                            # Validate critical attributes
                            if not hasattr(element, "GlobalId") or not element.GlobalId:
                                logger.debug(
                                    "Skipping element of type %s without GlobalId", element_type
                                )
                                continue

                            ifc_element = IFCElement(
                                global_id=element.GlobalId,
                                ifc_class=element.is_a(),
                                name=getattr(element, "Name", None),
                                description=getattr(element, "Description", None),
                                object_type=getattr(element, "ObjectType", None),
                                storey=storey_map.get(element.GlobalId),
                            )

                            # Extract properties with error handling
                            if self.extract_properties:
                                try:
                                    ifc_element.properties = self._get_element_properties(element)
                                except Exception as e:
                                    logger.debug(
                                        "Error extracting properties for %s: %s",
                                        element.GlobalId,
                                        e,
                                    )
                                    ifc_element.properties = {}

                            # Extract quantities with error handling
                            if self.extract_quantities:
                                try:
                                    ifc_element.quantities = self._get_element_quantities(element)
                                except Exception as e:
                                    logger.debug(
                                        "Error extracting quantities for %s: %s",
                                        element.GlobalId,
                                        e,
                                    )
                                    ifc_element.quantities = {}

                            # Extract materials with error handling
                            if self.extract_materials:
                                try:
                                    ifc_element.materials = self._get_element_materials(element)
                                except Exception as e:
                                    logger.debug(
                                        "Error extracting materials for %s: %s", element.GlobalId, e
                                    )
                                    ifc_element.materials = []

                            elements.append(ifc_element)
                            count += 1

                        except Exception as e:
                            logger.debug(
                                "Error extracting individual element of type %s: %s",
                                element_type,
                                e,
                            )
                            # Continue with next element

                except RuntimeError:
                    # Type not in schema
                    pass

        except Exception as e:
            logger.warning("Error extracting elements: %s", e)

        return elements

    def _build_storey_map(self, ifc_file: Any) -> dict[str, str]:
        """Build a mapping of element GlobalId to storey name."""
        storey_map: dict[str, str] = {}

        try:
            for storey in ifc_file.by_type("IfcBuildingStorey"):
                try:
                    # Get storey name with fallback
                    storey_name = getattr(storey, "Name", None) or getattr(
                        storey, "GlobalId", "Unknown"
                    )

                    # Get elements contained in this storey
                    for rel in getattr(storey, "ContainsElements", []) or []:
                        try:
                            for element in getattr(rel, "RelatedElements", []) or []:
                                if hasattr(element, "GlobalId") and element.GlobalId:
                                    storey_map[element.GlobalId] = storey_name
                        except Exception as e:
                            logger.debug("Error processing containment relationship: %s", e)

                except Exception as e:
                    logger.debug("Error processing storey: %s", e)

        except Exception as e:
            logger.warning("Error building storey map: %s", e)

        return storey_map

    def _get_element_properties(self, element: Any) -> dict[str, Any]:
        """Extract property sets for an element."""
        properties: dict[str, Any] = {}

        try:
            # Use ifcopenshell utility if available
            if hasattr(ifcopenshell.util, "element"):
                psets = ifcopenshell.util.element.get_psets(element)
                for pset_name, pset_props in psets.items():
                    if isinstance(pset_props, dict):
                        for prop_name, prop_value in pset_props.items():
                            if prop_name != "id":  # Skip internal id
                                properties[f"{pset_name}.{prop_name}"] = prop_value
            else:
                # Manual extraction
                for definition in getattr(element, "IsDefinedBy", []) or []:
                    if definition.is_a("IfcRelDefinesByProperties"):
                        pset = definition.RelatingPropertyDefinition
                        if pset.is_a("IfcPropertySet"):
                            pset_name = pset.Name or "Unknown"
                            for prop in pset.HasProperties or []:
                                prop_name = prop.Name
                                prop_value = self._get_property_value(prop)
                                properties[f"{pset_name}.{prop_name}"] = prop_value

        except Exception as e:
            logger.debug("Error extracting properties: %s", e)

        return properties

    def _get_property_value(self, prop: Any) -> Any:
        """Extract the value from an IFC property."""
        try:
            if prop.is_a("IfcPropertySingleValue"):
                if prop.NominalValue:
                    return prop.NominalValue.wrappedValue
            elif prop.is_a("IfcPropertyEnumeratedValue"):
                if prop.EnumerationValues:
                    return [v.wrappedValue for v in prop.EnumerationValues]
            elif prop.is_a("IfcPropertyListValue"):
                if prop.ListValues:
                    return [v.wrappedValue for v in prop.ListValues]
        except Exception:
            pass
        return None

    def _get_element_quantities(self, element: Any) -> dict[str, Any]:
        """Extract quantity sets for an element."""
        quantities: dict[str, Any] = {}

        try:
            for definition in getattr(element, "IsDefinedBy", []) or []:
                if definition.is_a("IfcRelDefinesByProperties"):
                    qset = definition.RelatingPropertyDefinition
                    if qset.is_a("IfcElementQuantity"):
                        qset_name = qset.Name or "Unknown"
                        for quantity in qset.Quantities or []:
                            q_name = quantity.Name
                            q_value = self._get_quantity_value(quantity)
                            if q_value is not None:
                                quantities[f"{qset_name}.{q_name}"] = q_value

        except Exception as e:
            logger.debug("Error extracting quantities: %s", e)

        return quantities

    def _get_quantity_value(self, quantity: Any) -> Any:
        """Extract the value from an IFC quantity."""
        try:
            if quantity.is_a("IfcQuantityLength"):
                return {"value": quantity.LengthValue, "unit": "m"}
            elif quantity.is_a("IfcQuantityArea"):
                return {"value": quantity.AreaValue, "unit": "m²"}
            elif quantity.is_a("IfcQuantityVolume"):
                return {"value": quantity.VolumeValue, "unit": "m³"}
            elif quantity.is_a("IfcQuantityWeight"):
                return {"value": quantity.WeightValue, "unit": "kg"}
            elif quantity.is_a("IfcQuantityCount"):
                return {"value": quantity.CountValue, "unit": "count"}
            elif quantity.is_a("IfcQuantityTime"):
                return {"value": quantity.TimeValue, "unit": "s"}
        except Exception:
            pass
        return None

    def _get_element_materials(self, element: Any) -> list[str]:
        """Extract material names for an element."""
        materials: list[str] = []

        try:
            for rel in getattr(element, "HasAssociations", []) or []:
                try:
                    if rel.is_a("IfcRelAssociatesMaterial"):
                        material = rel.RelatingMaterial
                        if material:
                            if material.is_a("IfcMaterial"):
                                mat_name = getattr(material, "Name", None)
                                if mat_name:
                                    materials.append(mat_name)
                            elif material.is_a("IfcMaterialLayerSet"):
                                for layer in getattr(material, "MaterialLayers", []) or []:
                                    layer_mat = getattr(layer, "Material", None)
                                    if layer_mat:
                                        mat_name = getattr(layer_mat, "Name", None)
                                        if mat_name:
                                            materials.append(mat_name)
                            elif material.is_a("IfcMaterialLayerSetUsage"):
                                layer_set = getattr(material, "ForLayerSet", None)
                                if layer_set:
                                    for layer in getattr(layer_set, "MaterialLayers", []) or []:
                                        layer_mat = getattr(layer, "Material", None)
                                        if layer_mat:
                                            mat_name = getattr(layer_mat, "Name", None)
                                            if mat_name:
                                                materials.append(mat_name)
                            elif material.is_a("IfcMaterialList"):
                                for mat in getattr(material, "Materials", []) or []:
                                    mat_name = getattr(mat, "Name", None)
                                    if mat_name:
                                        materials.append(mat_name)
                except Exception as e:
                    logger.debug("Error processing material association: %s", e)

        except Exception as e:
            logger.debug("Error extracting materials: %s", e)

        return materials

    def _elements_to_layers(self, element_counts: dict[str, int]) -> list[ExtractedLayer]:
        """Convert element counts to layer-like structure."""
        layers: list[ExtractedLayer] = []

        for ifc_class, count in element_counts.items():
            # Strip 'Ifc' prefix for display
            name = ifc_class[3:] if ifc_class.startswith("Ifc") else ifc_class
            layers.append(
                ExtractedLayer(
                    name=name,
                    entity_count=count,
                    is_on=True,
                )
            )

        return sorted(layers, key=lambda x: x.entity_count, reverse=True)

    def _extract_geometry_summary(self, ifc_file: Any) -> GeometrySummary:
        """Generate a geometry summary from IFC elements."""
        summary = GeometrySummary()

        try:
            # Count representation types
            for product in ifc_file.by_type("IfcProduct"):
                if not hasattr(product, "Representation") or not product.Representation:
                    continue

                summary.total_entities += 1

                rep = product.Representation
                for rep_item in rep.Representations or []:
                    rep_type = rep_item.RepresentationType
                    if rep_type == "SweptSolid":
                        summary.solids += 1
                    elif rep_type == "Brep":
                        summary.solids += 1
                    elif rep_type == "MappedRepresentation":
                        summary.meshes += 1
                    elif rep_type == "Curve2D":
                        summary.lines += 1

        except Exception as e:
            logger.warning("Error extracting geometry summary: %s", e)

        return summary

    def _extract_property_set_definitions(self, ifc_file: Any) -> list[dict[str, Any]]:
        """Extract unique property set definitions."""
        pset_defs: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        try:
            for pset in ifc_file.by_type("IfcPropertySet"):
                try:
                    pset_name = getattr(pset, "Name", None)
                    if pset_name and pset_name not in seen_names:
                        seen_names.add(pset_name)
                        props = []
                        for prop in getattr(pset, "HasProperties", []) or []:
                            try:
                                prop_name = getattr(prop, "Name", None)
                                if prop_name:
                                    props.append(
                                        {
                                            "name": prop_name,
                                            "type": prop.is_a(),
                                        }
                                    )
                            except Exception as e:
                                logger.debug("Error extracting property definition: %s", e)

                        pset_defs.append(
                            {
                                "name": pset_name,
                                "description": getattr(pset, "Description", None),
                                "properties": props,
                            }
                        )
                except Exception as e:
                    logger.debug("Error extracting property set: %s", e)

        except Exception as e:
            logger.warning("Error extracting property set definitions: %s", e)

        return pset_defs

    def _extract_type_objects(self, ifc_file: Any) -> list[dict[str, Any]]:
        """Extract type objects (e.g., IfcWallType, IfcDoorType)."""
        type_objects: list[dict[str, Any]] = []

        try:
            # Common type object classes
            type_classes = [
                "IfcWallType",
                "IfcDoorType",
                "IfcWindowType",
                "IfcSlabType",
                "IfcBeamType",
                "IfcColumnType",
                "IfcCoveringType",
                "IfcRoofType",
                "IfcStairType",
                "IfcFurnitureType",
            ]

            for type_class in type_classes:
                try:
                    for type_obj in ifc_file.by_type(type_class):
                        try:
                            if hasattr(type_obj, "GlobalId") and type_obj.GlobalId:
                                type_objects.append(
                                    {
                                        "global_id": type_obj.GlobalId,
                                        "type_class": type_obj.is_a(),
                                        "name": getattr(type_obj, "Name", None),
                                        "description": getattr(type_obj, "Description", None),
                                        "element_type": getattr(type_obj, "ElementType", None),
                                    }
                                )
                        except Exception as e:
                            logger.debug("Error extracting type object: %s", e)
                except RuntimeError:
                    # Type not in schema
                    pass

        except Exception as e:
            logger.warning("Error extracting type objects: %s", e)

        return type_objects
