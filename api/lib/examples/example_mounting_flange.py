"""
EXAMPLE: Rectangular Mounting Flange
Prompt: "Motor mount flange, 80x60mm, 8mm thick, 40mm center hole,
         4 x M6 bolt holes at corners (30mm from center)"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Bolt positions (centered coords)
    bolts = [(-25, -20), (25, -20), (-25, 20), (25, 20)]
    
    body = utils.create_mounting_flange(
        "MountFlange",
        length=80,
        width=60,
        thickness=8,
        center_hole_dia=40,
        bolt_hole_dia=6.5,  # M6 clearance
        bolt_positions=bolts
    )
    
    # Round corners
    v_edges = utils.select_edges(body, direction='Z')
    if v_edges:
        body = utils.apply_fillet(body, 5, edge_names=v_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
