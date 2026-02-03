"""
EXAMPLE: Control Knob
Prompt: "Control knob, 30mm diameter, 15mm tall, 6mm bore, knurled grip (12 flats)"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_knob(
        "Knob",
        diameter=30,
        height=15,
        knurl_count=12,
        bore_dia=6
    )
    
    # Add indicator line
    indicator = utils.create_box("indicator", 1, 12, 1,
                                 position=Base.Vector(-0.5, 0, 14))
    body = utils.cut_objects(body, indicator)
    
    # Round top edge
    top_edges = utils.select_edges(body, z_level=15)
    if top_edges:
        body = utils.apply_fillet(body, 2, edge_names=top_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
