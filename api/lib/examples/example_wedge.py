"""
EXAMPLE: Wedge (Ramp/Inclined block)
Prompt: "Wedge ramp, 50mm base, 30mm wide, rising from 0 to 20mm"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Wedge: defined by min/max coordinates
    # Creates a shape that tapers in X-Z plane
    body = utils.create_wedge(
        "Wedge",
        xmin=0, ymin=0, zmin=0,      # Starting corner
        x2min=0, z2min=0,             # Taper at min Y
        xmax=50, ymax=30, zmax=20,    # Ending corner
        x2max=50, z2max=0,            # Taper at max Y (flat at top X)
        position=Base.Vector(-25, -15, 0)  # Center it
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)


# Wedge is useful for ramps, doorstops, and angled supports:
def generate_doorstop(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Simple doorstop wedge
    body = utils.create_wedge(
        "Doorstop",
        xmin=0, ymin=0, zmin=0,
        x2min=0, z2min=0,
        xmax=80, ymax=40, zmax=25,
        x2max=80, z2max=0
    )
    
    # Add grip ridges on top (optional)
    for i in range(3):
        ridge = utils.create_box(f"Ridge_{i}", 80, 3, 2,
                                position=Base.Vector(0, 10 + i*10, 20))
        body = utils.cut_objects(body, ridge)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
