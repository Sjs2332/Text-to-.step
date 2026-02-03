"""
EXAMPLE: Shaft with Keyway
Prompt: "20mm diameter shaft, 100mm long, 6mm keyway (3mm deep, 80mm long)"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_shaft(
        "Shaft",
        diameter=20,
        length=100,
        keyway_width=6,
        keyway_depth=3,
        keyway_length=80
    )
    
    # Add chamfers on ends
    end_edges = utils.select_edges(body, edge_type='Circle', z_level=50)
    end_edges += utils.select_edges(body, edge_type='Circle', z_level=-50)
    if end_edges:
        body = utils.apply_chamfer(body, 1, edge_names=end_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
