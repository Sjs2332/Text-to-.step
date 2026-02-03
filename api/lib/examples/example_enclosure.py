"""
EXAMPLE: Enclosure with mounting bosses
Prompt: "110x80x45mm enclosure, 2.5mm walls, 3mm floor, R6 corners, 
         1° draft, 4 bosses (7mm dia, 6mm tall) in 85x55mm pattern"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Dimensions
    L, W, H = 110, 80, 45
    wall_t, floor_t = 2.5, 3.0
    corner_r, draft = 6.0, 1.0
    boss_dia, boss_h = 7.0, 6.0
    pattern = (85, 55)  # spacing
    
    # 1. Create enclosure base (handles box→draft→fillet→shell)
    body, floor_z = utils.create_enclosure_base(
        "Enclosure", L, W, H,
        wall_thickness=wall_t,
        floor_thickness=floor_t,
        corner_radius=corner_r,
        draft_angle=draft,
        open_face='+Z'
    )
    
    # 2. Boss positions (centered coords from 85x55 pattern)
    positions = [
        (-pattern[0]/2, -pattern[1]/2),
        ( pattern[0]/2, -pattern[1]/2),
        (-pattern[0]/2,  pattern[1]/2),
        ( pattern[0]/2,  pattern[1]/2),
    ]
    
    # 3. Add bosses
    body = utils.add_enclosure_bosses(
        body, positions,
        boss_dia=boss_dia,
        boss_height=boss_h,
        floor_z=floor_z,
        base_fillet=1.5
    )
    
    # 4. Internal fillet
    floor_edges = utils.select_edges(body, z_level=floor_z)
    if floor_edges:
        body = utils.apply_fillet(body, 2.0, edge_names=floor_edges)
    
    # 5. Rim fillet
    rim_edges = utils.select_edges(body, z_level=H/2)
    if rim_edges:
        body = utils.apply_fillet(body, 0.5, edge_names=rim_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
