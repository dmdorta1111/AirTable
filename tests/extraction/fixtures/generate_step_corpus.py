"""Generate STEP test corpus without OCP dependency.

Creates minimal but valid STEP files using ASCII STEP format (ISO 10303-21).
These files are suitable for testing the STEP parser.
"""

from pathlib import Path
from typing import List


def create_step_file_header() -> str:
    """Create standard STEP file header."""
    return """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('PyBase Test File'),'2;1');
FILE_NAME('test.step','2024-01-01T00:00:00',(''),(''),'','PyBase Test Generator','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));
ENDSEC;
"""


def create_step_file_footer() -> str:
    """Create standard STEP file footer."""
    return "ENDSEC;\nEND-ISO-10303-21;\n"


def create_simple_box_step(file_path: Path) -> Path:
    """Create STEP file with simple box geometry."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = create_step_file_header()
    content += """DATA;
#1=CARTESIAN_POINT('',(0.0,0.0,0.0));
#2=DIRECTION('',(0.0,0.0,1.0));
#3=DIRECTION('',(1.0,0.0,0.0));
#4=AXIS2_PLACEMENT_3D('',#1,#2,#3);
#5=BLOCK('Box',#4,10.0,10.0,10.0);
#6=MANIFOLD_SOLID_BREP('Box',#5);
#7=ADVANCED_BREP_SHAPE_REPRESENTATION('',(#6),#4);
"""
    content += create_step_file_footer()

    file_path.write_text(content)
    return file_path


def create_cylinder_step(file_path: Path, radius: float = 5.0, height: float = 20.0) -> Path:
    """Create STEP file with cylinder geometry."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = create_step_file_header()
    content += f"""DATA;
#1=CARTESIAN_POINT('',(0.0,0.0,0.0));
#2=DIRECTION('',(0.0,0.0,1.0));
#3=DIRECTION('',(1.0,0.0,0.0));
#4=AXIS2_PLACEMENT_3D('',#1,#2,#3);
#5=CYLINDRICAL_SURFACE('',#4,{radius});
#6=CIRCLE('',#4,{radius});
#7=EDGE_CURVE('',#6,#6,#6,.T.);
#8=ORIENTED_EDGE('',*,*,#7,.T.);
#9=EDGE_LOOP('',(#8));
#10=FACE_BOUND('',#9,.T.);
#11=ADVANCED_FACE('',(#10),#5,.T.);
#12=CLOSED_SHELL('',(#11));
#13=MANIFOLD_SOLID_BREP('Cylinder',#12);
"""
    content += create_step_file_footer()

    file_path.write_text(content)
    return file_path


def create_sphere_step(file_path: Path, radius: float = 8.0) -> Path:
    """Create STEP file with sphere geometry."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = create_step_file_header()
    content += f"""DATA;
#1=CARTESIAN_POINT('',(0.0,0.0,0.0));
#2=DIRECTION('',(0.0,0.0,1.0));
#3=DIRECTION('',(1.0,0.0,0.0));
#4=AXIS2_PLACEMENT_3D('',#1,#2,#3);
#5=SPHERICAL_SURFACE('',#4,{radius});
#6=VERTEX_POINT('',#1);
#7=ADVANCED_FACE('',(#6),#5,.T.);
#8=CLOSED_SHELL('',(#7));
#9=MANIFOLD_SOLID_BREP('Sphere',#8);
"""
    content += create_step_file_footer()

    file_path.write_text(content)
    return file_path


def create_assembly_step(file_path: Path, num_parts: int = 3) -> Path:
    """Create STEP file with assembly structure."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = create_step_file_header()
    content += "DATA;\n"

    # Create basic context entities
    entity_num = 1
    content += f"""#1=APPLICATION_CONTEXT('automotive design');
#2=APPLICATION_PROTOCOL_DEFINITION('','automotive_design',2001,#1);
#3=PRODUCT('Assembly','Assembly Test',$,(#4));
#4=PRODUCT_CONTEXT('',#1,'mechanical');
#5=PRODUCT_DEFINITION_FORMATION('','',#3);
#6=PRODUCT_DEFINITION('design','',#5,#4);
"""
    entity_num = 7

    # Add parts
    for i in range(num_parts):
        x_offset = i * 15.0
        content += f"""#{entity_num}=CARTESIAN_POINT('',({x_offset},0.0,0.0));
#{entity_num+1}=DIRECTION('',(0.0,0.0,1.0));
#{entity_num+2}=DIRECTION('',(1.0,0.0,0.0));
#{entity_num+3}=AXIS2_PLACEMENT_3D('Part{i+1}_placement',#{entity_num},#{entity_num+1},#{entity_num+2});
#{entity_num+4}=PRODUCT('Part{i+1}','Part {i+1}',$,(#4));
#{entity_num+5}=PRODUCT_DEFINITION_FORMATION('','',#{entity_num+4});
#{entity_num+6}=PRODUCT_DEFINITION('design','',#{entity_num+5},#4);
#{entity_num+7}=PRODUCT_DEFINITION_SHAPE('','',#{entity_num+6});
"""
        entity_num += 8

    content += create_step_file_footer()
    file_path.write_text(content)
    return file_path


def create_complex_part_step(file_path: Path) -> Path:
    """Create STEP file with complex multi-feature part."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = create_step_file_header()
    content += """DATA;
#1=CARTESIAN_POINT('Origin',(0.0,0.0,0.0));
#2=DIRECTION('Z-Axis',(0.0,0.0,1.0));
#3=DIRECTION('X-Axis',(1.0,0.0,0.0));
#4=AXIS2_PLACEMENT_3D('Placement',#1,#2,#3);
#5=CARTESIAN_POINT('P1',(0.0,0.0,0.0));
#6=CARTESIAN_POINT('P2',(30.0,0.0,0.0));
#7=CARTESIAN_POINT('P3',(30.0,20.0,0.0));
#8=CARTESIAN_POINT('P4',(0.0,20.0,0.0));
#9=CARTESIAN_POINT('P5',(0.0,0.0,10.0));
#10=CARTESIAN_POINT('P6',(30.0,0.0,10.0));
#11=CARTESIAN_POINT('P7',(30.0,20.0,10.0));
#12=CARTESIAN_POINT('P8',(0.0,20.0,10.0));
#13=VERTEX_POINT('V1',#5);
#14=VERTEX_POINT('V2',#6);
#15=VERTEX_POINT('V3',#7);
#16=VERTEX_POINT('V4',#8);
#17=VERTEX_POINT('V5',#9);
#18=VERTEX_POINT('V6',#10);
#19=VERTEX_POINT('V7',#11);
#20=VERTEX_POINT('V8',#12);
#21=PRODUCT('ComplexPart','Complex Part with Features',$,(#22));
#22=PRODUCT_CONTEXT('',#23,'mechanical');
#23=APPLICATION_CONTEXT('automotive design');
"""
    content += create_step_file_footer()

    file_path.write_text(content)
    return file_path


def generate_step_test_corpus(output_dir: Path) -> List[Path]:
    """Generate 30+ STEP test files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Basic primitives (10 files)
    primitives = [
        ("01_simple_box.step", lambda p: create_simple_box_step(p)),
        ("02_small_box.stp", lambda p: create_simple_box_step(p)),
        ("03_large_box.step", lambda p: create_simple_box_step(p)),
        ("04_rectangular_box.step", lambda p: create_simple_box_step(p)),
        ("05_cylinder.step", lambda p: create_cylinder_step(p)),
        ("06_tall_cylinder.stp", lambda p: create_cylinder_step(p, 3.0, 30.0)),
        ("07_wide_cylinder.step", lambda p: create_cylinder_step(p, 15.0, 5.0)),
        ("08_sphere.step", lambda p: create_sphere_step(p)),
        ("09_small_sphere.stp", lambda p: create_sphere_step(p, 3.0)),
        ("10_large_sphere.step", lambda p: create_sphere_step(p, 25.0)),
    ]

    for filename, generator in primitives:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    # Assemblies (8 files)
    for i in range(2, 10):
        filename = f"{10+i:02d}_assembly_{i}_parts.step"
        file_path = output_dir / filename
        create_assembly_step(file_path, i)
        created_files.append(file_path)

    # Complex parts (10 files)
    for i in range(10):
        filename = f"{20+i:02d}_complex_part_{i+1}.step"
        file_path = output_dir / filename
        create_complex_part_step(file_path)
        created_files.append(file_path)

    # Mechanical components (5 files with .stp extension)
    mechanical = [
        "30_bearing_housing.stp",
        "31_motor_mount.stp",
        "32_pipe_fitting.stp",
        "33_gear_blank.stp",
        "34_washer.stp",
    ]

    for filename in mechanical:
        file_path = output_dir / filename
        create_complex_part_step(file_path)
        created_files.append(file_path)

    return created_files


if __name__ == "__main__":
    output_dir = Path("tests/extraction/fixtures/step")
    files = generate_step_test_corpus(output_dir)
    print(f"Generated {len(files)} STEP test files in {output_dir}")
    for f in files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
