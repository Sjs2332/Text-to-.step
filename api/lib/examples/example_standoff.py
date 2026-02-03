"""
EXAMPLE: PCB Standoff
Prompt: "M3 standoff, 6mm OD, 10mm tall, 3.2mm through hole"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_standoff(
        "Standoff",
        outer_dia=6,
        inner_dia=3.2,
        height=10
    )
    
    # Chamfer both ends
    edges = utils.select_edges(body, edge_type='Circle')
    if edges:
        body = utils.apply_chamfer(body, 0.5, edge_names=edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)


# For multiple standoffs, use pattern:
def generate_pcb_standoffs(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Single standoff
    standoff = utils.create_standoff("Standoff", 6, 3.2, 10)
    
    # Pattern for 50x50mm PCB mounting
    body = utils.create_rectangular_pattern(
        standoff,
        Base.Vector(1, 0, 0), 50, 2,  # X direction
        Base.Vector(0, 1, 0), 50, 2   # Y direction
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
