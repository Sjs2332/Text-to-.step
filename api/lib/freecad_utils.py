import FreeCAD
import Part
import math
import Mesh
import os
from FreeCAD import Base
import logging

logger = logging.getLogger("text-to-cad-utils")
logger.setLevel(logging.INFO)


class PartUtils:
    def __init__(self, doc_name="Model"):
        self.doc = FreeCAD.newDocument(doc_name)

    # ==========================================================================
    # VALIDATION & SAFETY
    # ==========================================================================

    def _safe_path(self, path):
        """Prevents path traversal attacks."""
        base_dir = os.getcwd()
        tmp_dir = "/tmp"
        full_path = os.path.abspath(path)
        if not (full_path.startswith(base_dir) or full_path.startswith(tmp_dir)):
            raise PermissionError(f"Path {path} outside allowed directories")
        return full_path

    def _validate(self, obj, op_name):
        """Validates shape - raises on failure instead of silent return."""
        if obj is None:
            raise ValueError(f"{op_name}: returned None")
        if not hasattr(obj, 'Shape'):
            raise ValueError(f"{op_name}: no Shape attribute")
        if obj.Shape.isNull():
            raise ValueError(f"{op_name}: null shape")
        return obj

    def _log(self, obj, label):
        """Debug logging with volume/bbox."""
        if hasattr(obj, 'Shape') and not obj.Shape.isNull():
            bb = obj.Shape.BoundBox
            logger.info(f"{label}: V={obj.Shape.Volume:.1f} [{bb.XLength:.1f}x{bb.YLength:.1f}x{bb.ZLength:.1f}]")

    # ==========================================================================
    # BASIC PRIMITIVES
    # ==========================================================================

    def create_box(self, name, length, width, height, center=False, position=None):
        """Creates box. Use center=True for symmetric positioning."""
        obj = self.doc.addObject("Part::Box", name)
        obj.Length, obj.Width, obj.Height = length, width, height
        if center:
            obj.Placement.Base = Base.Vector(-length/2, -width/2, -height/2)
        if position:
            obj.Placement.Base = position
        self.doc.recompute()
        return self._validate(obj, f"create_box({name})")

    def create_cylinder(self, name, radius, height, center=False, position=None, direction=None):
        """Creates cylinder. direction rotates axis from Z."""
        obj = self.doc.addObject("Part::Cylinder", name)
        obj.Radius, obj.Height = radius, height
        if center:
            obj.Placement.Base = Base.Vector(0, 0, -height/2)
        if position:
            obj.Placement.Base = position
        if direction:
            obj.Placement.Rotation = FreeCAD.Rotation(Base.Vector(0,0,1), direction)
        self.doc.recompute()
        return self._validate(obj, f"create_cylinder({name})")

    def create_sphere(self, name, radius, position=None):
        obj = self.doc.addObject("Part::Sphere", name)
        obj.Radius = radius
        if position:
            obj.Placement.Base = position
        self.doc.recompute()
        return self._validate(obj, f"create_sphere({name})")

    def create_cone(self, name, radius1, radius2, height, position=None):
        """radius1=bottom, radius2=top."""
        obj = self.doc.addObject("Part::Cone", name)
        obj.Radius1, obj.Radius2, obj.Height = radius1, radius2, height
        if position:
            obj.Placement.Base = position
        self.doc.recompute()
        return self._validate(obj, f"create_cone({name})")

    def create_torus(self, name, radius1, radius2, position=None):
        """radius1=major (center to tube), radius2=minor (tube radius)."""
        obj = self.doc.addObject("Part::Torus", name)
        obj.Radius1, obj.Radius2 = radius1, radius2
        if position:
            obj.Placement.Base = position
        self.doc.recompute()
        return self._validate(obj, f"create_torus({name})")

    def create_wedge(self, name, xmin, ymin, zmin, x2min, z2min, xmax, ymax, zmax, x2max, z2max, position=None):
        """Creates a wedge/ramp shape."""
        obj = self.doc.addObject("Part::Wedge", name)
        obj.Xmin, obj.Ymin, obj.Zmin = xmin, ymin, zmin
        obj.X2min, obj.Z2min = x2min, z2min
        obj.Xmax, obj.Ymax, obj.Zmax = xmax, ymax, zmax
        obj.X2max, obj.Z2max = x2max, z2max
        if position:
            obj.Placement.Base = position
        self.doc.recompute()
        return self._validate(obj, f"create_wedge({name})")

    # ==========================================================================
    # HOLE FEATURES (for cutting)
    # ==========================================================================

    def create_hole(self, name, diameter, depth, position=None):
        """Simple through/blind hole."""
        return self.create_cylinder(name, diameter/2, depth, position=position)

    def create_counterbore(self, name, hole_dia, hole_depth, cb_dia, cb_depth, position=None):
        """Counterbore: hole + larger recess for socket head bolts."""
        hole = self.create_cylinder(f"{name}_hole", hole_dia/2, hole_depth)
        cb = self.create_cylinder(f"{name}_cb", cb_dia/2, cb_depth,
                                  position=Base.Vector(0, 0, hole_depth - cb_depth))
        tool = self.fuse_objects([hole, cb])
        if position:
            tool.Placement.Base = position
        self.doc.recompute()
        return self._validate(tool, f"create_counterbore({name})")

    def create_countersink(self, name, hole_dia, hole_depth, cs_dia, cs_angle=90, position=None):
        """Countersink: hole + conical recess for flat head screws."""
        hole = self.create_cylinder(f"{name}_hole", hole_dia/2, hole_depth)
        cs_depth = (cs_dia - hole_dia) / 2 / math.tan(math.radians(cs_angle/2))
        cone = self.create_cone(f"{name}_cs", cs_dia/2, hole_dia/2, cs_depth,
                               position=Base.Vector(0, 0, hole_depth - cs_depth))
        tool = self.fuse_objects([hole, cone])
        if position:
            tool.Placement.Base = position
        self.doc.recompute()
        return self._validate(tool, f"create_countersink({name})")

    def create_slot(self, name, length, width, depth, position=None):
        """Slot: rounded-end channel (like adjustment slots)."""
        r = width / 2
        box = self.create_box(f"{name}_box", length - width, width, depth, center=True)
        c1 = self.create_cylinder(f"{name}_c1", r, depth, center=True,
                                  position=Base.Vector(-(length-width)/2, 0, 0))
        c2 = self.create_cylinder(f"{name}_c2", r, depth, center=True,
                                  position=Base.Vector((length-width)/2, 0, 0))
        tool = self.fuse_objects([box, c1, c2])
        if position:
            tool.Placement.Base = position
        self.doc.recompute()
        return self._validate(tool, f"create_slot({name})")

    def create_pocket(self, name, length, width, depth, corner_radius=0, position=None):
        """Rectangular pocket with optional corner radius."""
        if corner_radius > 0:
            # Create rounded rectangle pocket
            box = self.create_box(f"{name}_box", length, width, depth, center=True)
            v_edges = self.select_edges(box, direction='Z')
            if v_edges:
                box = self.apply_fillet(box, corner_radius, edge_names=v_edges)
            if position:
                box.Placement.Base = position
            return box
        else:
            return self.create_box(name, length, width, depth, center=True, position=position)

    # ==========================================================================
    # BOSS/STANDOFF FEATURES
    # ==========================================================================

    def create_boss(self, name, outer_dia, height, hole_dia=None, position=None):
        """Mounting boss with optional center hole for screws."""
        boss = self.create_cylinder(f"{name}_outer", outer_dia/2, height, position=position)
        if hole_dia and hole_dia > 0:
            pos = position if position else Base.Vector(0,0,0)
            hole = self.create_cylinder(f"{name}_hole", hole_dia/2, height * 1.1,
                                       position=Base.Vector(pos.x, pos.y, pos.z - height*0.05))
            boss = self.cut_objects(boss, hole)
        return self._validate(boss, f"create_boss({name})")

    def create_standoff(self, name, outer_dia, inner_dia, height, position=None):
        """Hollow standoff/spacer."""
        return self.create_boss(name, outer_dia, height, hole_dia=inner_dia, position=position)

    def create_rib(self, name, length, height, thickness, position=None, direction='X'):
        """Structural rib for reinforcement."""
        if direction == 'Y':
            rib = self.create_box(name, thickness, length, height, center=True, position=position)
        else:
            rib = self.create_box(name, length, thickness, height, center=True, position=position)
        return self._validate(rib, f"create_rib({name})")

    def create_gusset(self, name, width, height, thickness, position=None):
        """Triangular gusset/support bracket."""
        # Create triangular profile using wedge
        gusset = self.create_wedge(name, 0, 0, 0, 0, 0, width, thickness, height, width, 0)
        if position:
            gusset.Placement.Base = position
        return self._validate(gusset, f"create_gusset({name})")

    # ==========================================================================
    # ENCLOSURE MEGA-FUNCTIONS
    # ==========================================================================

    def create_enclosure_base(self, name, length, width, height,
                              wall_thickness, floor_thickness=None,
                              corner_radius=0, draft_angle=0, open_face='+Z'):
        """
        Complete enclosure base in one call: box → draft → fillet → shell.
        Returns: (body, internal_floor_z)
        """
        if floor_thickness is None:
            floor_thickness = wall_thickness

        logger.info(f"create_enclosure_base: {length}x{width}x{height}, wall={wall_thickness}, floor={floor_thickness}")

        # 1. Box
        body = self.create_box(f"{name}_box", length, width, height, center=True)

        # 2. Draft BEFORE fillets
        if draft_angle != 0:
            body = self.apply_draft(body, Base.Vector(0,0,1), -abs(draft_angle), neutral_plane_z=-height/2)

        # 3. Corner fillets
        if corner_radius > 0:
            v_edges = self.select_edges(body, direction='Z')
            if v_edges:
                body = self.apply_fillet(body, corner_radius, edge_names=v_edges)

        # 4. Shell
        body = self.create_shell(body, wall_thickness, open_face_direction=open_face)

        internal_floor_z = -height/2 + floor_thickness
        logger.info(f"Enclosure complete. Internal floor Z = {internal_floor_z}")
        return body, internal_floor_z

    def add_enclosure_bosses(self, body, positions, boss_dia, boss_height,
                            floor_z, hole_dia=None, base_fillet=0):
        """
        Add mounting bosses to enclosure.
        positions: list of (x, y) in CENTERED coordinates
        """
        logger.info(f"Adding {len(positions)} bosses: dia={boss_dia}, h={boss_height}")

        bosses = []
        for i, (x, y) in enumerate(positions):
            boss = self.create_boss(f"Boss_{i}", boss_dia, boss_height,
                                   hole_dia=hole_dia,
                                   position=Base.Vector(x, y, floor_z))
            bosses.append(boss)

        body = self.fuse_objects([body] + bosses)

        if base_fillet > 0:
            edges = self.select_edges(body, edge_type='Circle', z_level=floor_z)
            if edges:
                body = self.apply_fillet(body, base_fillet, edge_names=edges)

        return body

    # ==========================================================================
    # BRACKET MEGA-FUNCTIONS
    # ==========================================================================

    def create_l_bracket(self, name, leg1_length, leg2_length, width, thickness,
                        hole_dia=0, hole_positions=None, fillet_radius=0):
        """
        L-shaped bracket.
        hole_positions: list of (leg, offset) where leg=1 or 2, offset from corner
        """
        # Vertical leg
        leg1 = self.create_box(f"{name}_leg1", thickness, width, leg1_length)
        # Horizontal leg
        leg2 = self.create_box(f"{name}_leg2", leg2_length, width, thickness,
                              position=Base.Vector(0, 0, 0))

        body = self.fuse_objects([leg1, leg2])

        # Inside corner fillet
        if fillet_radius > 0:
            # Select the inside corner edge
            inside_edges = self.select_edges(body, direction='Y', z_level=thickness)
            if inside_edges:
                body = self.apply_fillet(body, fillet_radius, edge_names=inside_edges)

        # Holes
        if hole_dia > 0 and hole_positions:
            for leg, offset in hole_positions:
                if leg == 1:  # Vertical leg
                    pos = Base.Vector(-thickness/2, width/2, offset)
                    hole = self.create_cylinder(f"{name}_hole", hole_dia/2, thickness*2,
                                               position=pos, direction=Base.Vector(1,0,0))
                else:  # Horizontal leg
                    pos = Base.Vector(offset, width/2, -thickness/2)
                    hole = self.create_cylinder(f"{name}_hole", hole_dia/2, thickness*2,
                                               position=pos)
                body = self.cut_objects(body, hole)

        return self._validate(body, f"create_l_bracket({name})")

    def create_u_bracket(self, name, width, height, depth, thickness,
                        hole_dia=0, holes_per_leg=0, fillet_radius=0):
        """
        U-shaped bracket (channel).
        """
        # Base
        base = self.create_box(f"{name}_base", width, depth, thickness)
        # Left leg
        left = self.create_box(f"{name}_left", thickness, depth, height,
                              position=Base.Vector(0, 0, thickness))
        # Right leg
        right = self.create_box(f"{name}_right", thickness, depth, height,
                               position=Base.Vector(width - thickness, 0, thickness))

        body = self.fuse_objects([base, left, right])

        # Fillets on inside corners
        if fillet_radius > 0:
            inside_edges = self.select_edges(body, direction='Y', z_level=thickness)
            if inside_edges:
                body = self.apply_fillet(body, fillet_radius, edge_names=inside_edges)

        # Holes in legs
        if hole_dia > 0 and holes_per_leg > 0:
            spacing = height / (holes_per_leg + 1)
            for i in range(holes_per_leg):
                z = thickness + spacing * (i + 1)
                # Left leg hole
                hole_l = self.create_cylinder(f"{name}_hole_l{i}", hole_dia/2, thickness*2,
                                             position=Base.Vector(-thickness/2, depth/2, z),
                                             direction=Base.Vector(1,0,0))
                body = self.cut_objects(body, hole_l)
                # Right leg hole
                hole_r = self.create_cylinder(f"{name}_hole_r{i}", hole_dia/2, thickness*2,
                                             position=Base.Vector(width-thickness/2, depth/2, z),
                                             direction=Base.Vector(1,0,0))
                body = self.cut_objects(body, hole_r)

        return self._validate(body, f"create_u_bracket({name})")

    def create_angle_bracket(self, name, leg1, leg2, width, thickness,
                            hole_dia=0, holes_per_leg=1, fillet_radius=0):
        """
        90-degree angle bracket with equal or unequal legs.
        """
        return self.create_l_bracket(name, leg1, leg2, width, thickness,
                                     hole_dia=hole_dia,
                                     hole_positions=[(1, leg1/2), (2, leg2/2)] if hole_dia > 0 else None,
                                     fillet_radius=fillet_radius)

    def create_flat_bracket(self, name, length, width, thickness, hole_dia=0, hole_count=2):
        """Simple flat bracket with holes."""
        body = self.create_box(name, length, width, thickness, center=True)

        if hole_dia > 0 and hole_count > 0:
            spacing = length / (hole_count + 1)
            for i in range(hole_count):
                x = -length/2 + spacing * (i + 1)
                hole = self.create_cylinder(f"{name}_hole_{i}", hole_dia/2, thickness*2,
                                           position=Base.Vector(x, 0, -thickness))
                body = self.cut_objects(body, hole)

        return self._validate(body, f"create_flat_bracket({name})")

    # ==========================================================================
    # FLANGE MEGA-FUNCTIONS
    # ==========================================================================

    def create_pipe_flange(self, name, outer_dia, inner_dia, thickness,
                          bolt_circle_dia, bolt_hole_dia, bolt_count,
                          hub_dia=0, hub_height=0):
        """
        Pipe flange with bolt holes in circular pattern.
        """
        # Main flange disc
        flange = self.create_cylinder(f"{name}_flange", outer_dia/2, thickness)

        # Hub (raised center)
        if hub_dia > 0 and hub_height > 0:
            hub = self.create_cylinder(f"{name}_hub", hub_dia/2, hub_height,
                                       position=Base.Vector(0, 0, thickness))
            flange = self.fuse_objects([flange, hub])
            total_height = thickness + hub_height
        else:
            total_height = thickness

        # Center bore
        bore = self.create_cylinder(f"{name}_bore", inner_dia/2, total_height * 1.1,
                                   position=Base.Vector(0, 0, -total_height*0.05))
        flange = self.cut_objects(flange, bore)

        # Bolt holes
        angle_step = 360 / bolt_count
        for i in range(bolt_count):
            angle = math.radians(i * angle_step)
            x = (bolt_circle_dia/2) * math.cos(angle)
            y = (bolt_circle_dia/2) * math.sin(angle)
            hole = self.create_cylinder(f"{name}_bolt_{i}", bolt_hole_dia/2, thickness*1.1,
                                       position=Base.Vector(x, y, -thickness*0.05))
            flange = self.cut_objects(flange, hole)

        return self._validate(flange, f"create_pipe_flange({name})")

    def create_mounting_flange(self, name, length, width, thickness,
                              center_hole_dia, bolt_hole_dia=0, bolt_positions=None):
        """
        Rectangular mounting flange with center hole and bolt holes.
        bolt_positions: list of (x, y) coordinates
        """
        flange = self.create_box(f"{name}_base", length, width, thickness, center=True)

        # Center hole
        center = self.create_cylinder(f"{name}_center", center_hole_dia/2, thickness*1.1,
                                     position=Base.Vector(0, 0, -thickness*0.55))
        flange = self.cut_objects(flange, center)

        # Bolt holes
        if bolt_hole_dia > 0 and bolt_positions:
            for i, (x, y) in enumerate(bolt_positions):
                hole = self.create_cylinder(f"{name}_bolt_{i}", bolt_hole_dia/2, thickness*1.1,
                                           position=Base.Vector(x, y, -thickness*0.55))
                flange = self.cut_objects(flange, hole)

        return self._validate(flange, f"create_mounting_flange({name})")

    # ==========================================================================
    # GEAR FUNCTIONS
    # ==========================================================================

    def create_spur_gear(self, name, module, teeth, thickness, bore_dia=0,
                        pressure_angle=20, hub_dia=0, hub_height=0):
        """
        Creates involute spur gear.
        module: tooth size (pitch_dia = module * teeth)
        """
        pitch_dia = module * teeth
        addendum = module
        dedendum = 1.25 * module
        outer_dia = pitch_dia + 2 * addendum
        root_dia = pitch_dia - 2 * dedendum

        # Simplified gear: create outer cylinder, cut tooth gaps
        gear = self.create_cylinder(f"{name}_blank", outer_dia/2, thickness)

        # Create tooth cutter (simplified as wedge shapes)
        tooth_angle = 360 / teeth
        cutter_width = module * 1.5

        for i in range(teeth):
            angle = math.radians(i * tooth_angle + tooth_angle/2)
            # Position at root circle
            x = (root_dia/2 + dedendum/2) * math.cos(angle)
            y = (root_dia/2 + dedendum/2) * math.sin(angle)
            
            cutter = self.create_box(f"{name}_cut_{i}", cutter_width, dedendum*2, thickness*1.1,
                                    center=True)
            cutter.Placement.Base = Base.Vector(x, y, -thickness*0.05)
            cutter.Placement.Rotation = FreeCAD.Rotation(Base.Vector(0,0,1), math.degrees(angle))
            gear = self.cut_objects(gear, cutter)

        # Hub
        if hub_dia > 0 and hub_height > 0:
            hub = self.create_cylinder(f"{name}_hub", hub_dia/2, hub_height,
                                       position=Base.Vector(0, 0, thickness))
            gear = self.fuse_objects([gear, hub])

        # Bore
        if bore_dia > 0:
            total_h = thickness + (hub_height if hub_height > 0 else 0)
            bore = self.create_cylinder(f"{name}_bore", bore_dia/2, total_h*1.1,
                                       position=Base.Vector(0, 0, -total_h*0.05))
            gear = self.cut_objects(gear, bore)

        return self._validate(gear, f"create_spur_gear({name})")

    def create_pulley(self, name, outer_dia, bore_dia, width,
                     groove_count=1, groove_depth=3, groove_angle=40):
        """
        V-belt pulley with grooves.
        """
        pulley = self.create_cylinder(f"{name}_blank", outer_dia/2, width, center=True)

        # Cut grooves
        groove_spacing = width / (groove_count + 1)
        for i in range(groove_count):
            z = -width/2 + groove_spacing * (i + 1)
            # V-groove is two cones meeting at center
            groove_r = outer_dia/2 + groove_depth
            groove = self.create_torus(f"{name}_groove_{i}", outer_dia/2, groove_depth,
                                       position=Base.Vector(0, 0, z))
            pulley = self.cut_objects(pulley, groove)

        # Bore
        bore = self.create_cylinder(f"{name}_bore", bore_dia/2, width*1.1, center=True)
        pulley = self.cut_objects(pulley, bore)

        return self._validate(pulley, f"create_pulley({name})")

    # ==========================================================================
    # REVOLVED PARTS
    # ==========================================================================

    def create_tube(self, name, outer_dia, inner_dia, length, position=None):
        """Simple tube/pipe."""
        outer = self.create_cylinder(f"{name}_outer", outer_dia/2, length, position=position)
        inner = self.create_cylinder(f"{name}_inner", inner_dia/2, length*1.1,
                                    position=Base.Vector(
                                        position.x if position else 0,
                                        position.y if position else 0,
                                        (position.z if position else 0) - length*0.05
                                    ))
        return self.cut_objects(outer, inner)

    def create_bushing(self, name, outer_dia, inner_dia, length, flange_dia=0, flange_thickness=0):
        """Bushing/bearing sleeve with optional flange."""
        body = self.create_tube(name, outer_dia, inner_dia, length)

        if flange_dia > 0 and flange_thickness > 0:
            flange = self.create_cylinder(f"{name}_flange", flange_dia/2, flange_thickness)
            body = self.fuse_objects([body, flange])

        return self._validate(body, f"create_bushing({name})")

    def create_shaft(self, name, diameter, length, keyway_width=0, keyway_depth=0, keyway_length=0):
        """Shaft with optional keyway."""
        shaft = self.create_cylinder(f"{name}_shaft", diameter/2, length, center=True)

        if keyway_width > 0 and keyway_depth > 0:
            kw_len = keyway_length if keyway_length > 0 else length * 0.8
            keyway = self.create_box(f"{name}_keyway", keyway_width, kw_len, keyway_depth,
                                    center=True,
                                    position=Base.Vector(0, 0, diameter/2 - keyway_depth/2))
            shaft = self.cut_objects(shaft, keyway)

        return self._validate(shaft, f"create_shaft({name})")

    def create_knob(self, name, diameter, height, knurl_count=0, bore_dia=0):
        """Control knob with optional knurling (simplified as flats)."""
        knob = self.create_cylinder(f"{name}_body", diameter/2, height)

        # Add grip flats
        if knurl_count > 0:
            flat_depth = diameter * 0.05
            for i in range(knurl_count):
                angle = math.radians(i * 360 / knurl_count)
                x = (diameter/2 + flat_depth/2) * math.cos(angle)
                y = (diameter/2 + flat_depth/2) * math.sin(angle)
                flat = self.create_box(f"{name}_flat_{i}", flat_depth*2, flat_depth*2, height*1.1,
                                      center=True, position=Base.Vector(x, y, height/2))
                knob = self.cut_objects(knob, flat)

        if bore_dia > 0:
            bore = self.create_cylinder(f"{name}_bore", bore_dia/2, height*1.1,
                                       position=Base.Vector(0, 0, -height*0.05))
            knob = self.cut_objects(knob, bore)

        return self._validate(knob, f"create_knob({name})")

    # ==========================================================================
    # TRANSFORMATIONS
    # ==========================================================================

    def move_object(self, obj, vector):
        obj.Placement.Base = obj.Placement.Base + vector
        self.doc.recompute()
        return obj

    def rotate_object(self, obj, axis, angle):
        """Rotates by angle (degrees) around axis."""
        rotation = FreeCAD.Rotation(axis, angle)
        obj.Placement.Rotation = rotation.multiply(obj.Placement.Rotation)
        self.doc.recompute()
        return obj

    def mirror_object(self, obj, normal):
        """Mirrors across plane through origin with given normal."""
        mirror = self.doc.addObject("Part::Mirroring", f"Mirror_{obj.Name}")
        mirror.Source = obj
        mirror.Normal = normal
        self.doc.recompute()
        return self._validate(mirror, "mirror_object")

    def copy_object(self, obj, new_name=None):
        if new_name is None:
            new_name = f"{obj.Name}_copy"
        new_obj = self.doc.addObject("Part::Feature", new_name)
        new_obj.Shape = obj.Shape.copy()
        self.doc.recompute()
        return self._validate(new_obj, f"copy_object({new_name})")

    def center_object(self, obj, axes="XYZ"):
        """Centers object on specified axes."""
        bbox = obj.Shape.BoundBox
        move = Base.Vector(0, 0, 0)
        if "X" in axes: move.x = -bbox.Center.x
        if "Y" in axes: move.y = -bbox.Center.y
        if "Z" in axes: move.z = -bbox.Center.z
        obj.Placement.move(move)
        self.doc.recompute()
        return obj

    # ==========================================================================
    # PATTERNS
    # ==========================================================================

    def create_linear_pattern(self, obj, direction, spacing, count):
        """Linear array of objects."""
        if count <= 1:
            return obj
        parts = [obj]
        for i in range(1, count):
            new_obj = self.copy_object(obj, f"{obj.Name}_lin_{i}")
            new_obj.Placement.Base = obj.Placement.Base + (direction.normalize() * spacing * i)
            parts.append(new_obj)
        self.doc.recompute()
        return self.fuse_objects(parts)

    def create_rectangular_pattern(self, obj, dir1, spacing1, count1, dir2, spacing2, count2):
        """2D rectangular array."""
        parts = []
        for i in range(count1):
            for j in range(count2):
                if i == 0 and j == 0:
                    parts.append(obj)
                else:
                    new_obj = self.copy_object(obj, f"{obj.Name}_rect_{i}_{j}")
                    offset = (dir1.normalize() * spacing1 * i) + (dir2.normalize() * spacing2 * j)
                    new_obj.Placement.Base = obj.Placement.Base + offset
                    parts.append(new_obj)
        self.doc.recompute()
        return self.fuse_objects(parts)

    def create_polar_pattern(self, obj, center, axis, count, angle=360):
        """Circular array around axis."""
        if count <= 1:
            return obj
        angle_step = angle / count
        parts = [obj]
        for i in range(1, count):
            new_obj = self.copy_object(obj, f"{obj.Name}_pol_{i}")
            new_obj.Shape.rotate(center, axis, angle_step * i)
            parts.append(new_obj)
        self.doc.recompute()
        return self.fuse_objects(parts)

    # ==========================================================================
    # EDGE/FACE SELECTION
    # ==========================================================================

    def select_edges(self, obj, edge_type=None, direction=None, z_level=None,
                    min_radius=None, max_radius=None):
        """
        Select edges by criteria.
        edge_type: 'Circle', 'Line', 'BSpline'
        direction: 'X', 'Y', 'Z'
        z_level: edges at this Z (±0.5mm tolerance)
        min/max_radius: distance from Z axis
        """
        selected = []
        for i, edge in enumerate(obj.Shape.Edges):
            match = True

            if edge_type and edge_type not in str(type(edge.Curve)):
                match = False

            if direction and match:
                try:
                    v = edge.tangentAt(edge.Length / 2.0 if edge.Length > 0 else 0)
                    # CUT-THROAT FIX: Stricter tolerances (was 0.9)
                    # v.z (dot product with Z) should be near 0 for horizontal, near 1 for vertical
                    if direction == 'Z':
                        if abs(v.z) < 0.999: match = False
                    elif direction == 'X':
                        if abs(v.x) < 0.999: match = False
                    elif direction == 'Y':
                        if abs(v.y) < 0.999: match = False
                except:
                    match = False

            if z_level is not None and match:
                z_match = any(abs(v.Z - z_level) < 0.5 for v in edge.Vertexes)
                if not z_match:
                    match = False

            if (min_radius is not None or max_radius is not None) and match:
                com = edge.CenterOfMass
                dist = math.sqrt(com.x**2 + com.y**2)
                if min_radius and dist < min_radius: match = False
                if max_radius and dist > max_radius: match = False

            if match:
                selected.append(f"Edge{i+1}")

        logger.info(f"select_edges({edge_type}, {direction}, z={z_level}) -> {len(selected)}")
        return selected

    def select_faces(self, obj, normal=None, z_level=None):
        """Select faces by normal direction or Z level."""
        selected = []
        for i, face in enumerate(obj.Shape.Faces):
            match = True

            if normal and match:
                try:
                    n = face.normalAt(0.5, 0.5).normalize()
                    if abs(n.dot(normal.normalize())) < 0.9:
                        match = False
                except:
                    match = False

            if z_level is not None and match:
                if abs(face.CenterOfMass.z - z_level) > 0.5:
                    match = False

            if match:
                selected.append(f"Face{i+1}")

        return selected

    def select_faces_by_normal(self, obj, normal_vector):
        """Legacy compatibility."""
        return self.select_faces(obj, normal=normal_vector)

    # ==========================================================================
    # FEATURES (Draft, Shell, Fillet, Chamfer)
    # ==========================================================================

    def apply_draft(self, obj, pull_direction, angle, neutral_plane_z=0):
        """
        Draft angle on vertical faces. MUST call BEFORE fillets!
        angle: negative = outward draft
        """
        # Skip if angle is 0
        if abs(angle) < 0.01:
            return obj
            
        faces = [f for f in obj.Shape.Faces if abs(f.normalAt(0.5,0.5).dot(pull_direction)) < 0.1]

        if not faces:
            # CUT-THROAT FIX: Fail if no draftable faces found
            raise ValueError(f"apply_draft: No vertical faces found for drafting. Ensure draft is applied BEFORE fillets/chamfers.")

        logger.info(f"apply_draft: {len(faces)} faces at {angle}°")

        try:
            # Try using Part.makeDraft (static method)
            if hasattr(obj.Shape, 'makeDraft'):
                new_shape = obj.Shape.makeDraft(faces, Base.Vector(0,0,neutral_plane_z),
                                                pull_direction, math.radians(angle))
            else:
                raise ValueError("apply_draft: FreeCAD version too old (makeDraft not found)")
                
            if new_shape.isNull():
                raise ValueError("makeDraft returned null shape")

            draft = self.doc.addObject("Part::Feature", f"Draft_{obj.Name}")
            draft.Shape = new_shape
            self.doc.recompute()
            return self._validate(draft, "apply_draft")

        except Exception as e:
            # CUT-THROAT FIX: No silent failure
            raise ValueError(f"apply_draft failed: {e}")

    def create_shell(self, obj, thickness, open_face_direction='+Z'):
        """Shell/hollow operation using B-Rep makeThickSolid."""
        direction_map = {
            '+Z': Base.Vector(0,0,1), '-Z': Base.Vector(0,0,-1),
            '+X': Base.Vector(1,0,0), '-X': Base.Vector(-1,0,0),
            '+Y': Base.Vector(0,1,0), '-Y': Base.Vector(0,-1,0)
        }
        target = direction_map.get(open_face_direction, Base.Vector(0,0,1)).normalize()

        # Find faces to remove (open faces)
        faces_to_remove = []
        for i, f in enumerate(obj.Shape.Faces):
            try:
                n = f.normalAt(0.5, 0.5)
                if n.dot(target) > 0.9:
                    faces_to_remove.append(obj.Shape.Faces[i])
            except:
                pass

        logger.info(f"create_shell: thickness={thickness}, removing {len(faces_to_remove)} faces")

        if not faces_to_remove:
            logger.warning("create_shell: no faces to remove found")
            return obj

        try:
            # Try different FreeCAD API methods for shell/thick solid
            shape = obj.Shape
            
            # Method 1: makeThickness (FreeCAD 0.21+)
            if hasattr(shape, 'makeThickness'):
                new_shape = shape.makeThickness(faces_to_remove, -thickness, 0.001)
            # Method 2: makeThickSolid (older versions)
            elif hasattr(shape, 'makeThickSolid'):
                new_shape = shape.makeThickSolid(faces_to_remove, -thickness, 0.001)
            else:
                raise ValueError("No shell method available (makeThickness or makeThickSolid)")
            
            if new_shape.isNull():
                raise ValueError("Shell operation returned null")
            
            shell = self.doc.addObject("Part::Feature", f"Shell_{obj.Name}")
            shell.Shape = new_shape
            self.doc.recompute()
            return self._validate(shell, "create_shell")
        except Exception as e:
            raise ValueError(f"create_shell failed: {e}")

    def apply_fillet(self, obj, radius, edge_names=None, direction=None, z_level=None):
        """Fillet edges. Select by edge_names OR by direction/z_level.
        Automatically clamps radius to safe value if too large for edges."""
        if not edge_names:
            edge_names = self.select_edges(obj, direction=direction, z_level=z_level)
        if not edge_names:
            logger.warning(f"apply_fillet(R{radius}): no edges")
            return obj

        logger.info(f"apply_fillet: R{radius} on {len(edge_names)} edges")

        try:
            edges = []
            min_edge_len = float('inf')
            for name in edge_names:
                idx = int(name.replace("Edge", "")) - 1
                if 0 <= idx < len(obj.Shape.Edges):
                    edge = obj.Shape.Edges[idx]
                    edges.append(edge)
                    # Track minimum edge length for radius clamping
                    if edge.Length < min_edge_len:
                        min_edge_len = edge.Length

            if not edges:
                return obj

            # CUT-THROAT FIX: No silent clamping.
            # If radius is too large, FAIL LOUDLY so the agent knows to fix it.
            max_safe_radius = (min_edge_len / 2) - 0.01
            if radius > max_safe_radius:
                raise ValueError(f"Fillet R{radius} too large for edge length {min_edge_len:.2f}. Max safe radius is {max_safe_radius:.2f}")

            new_shape = obj.Shape.makeFillet(radius, edges)
            if new_shape.isNull():
                raise ValueError(f"makeFillet(R{radius}) returned null")

            fillet = self.doc.addObject("Part::Feature", f"Fillet_{obj.Name}")
            fillet.Shape = new_shape
            self.doc.recompute()
            return self._validate(fillet, "apply_fillet")

        except Exception as e:
            # CUT-THROAT FIX: No silent failure
            raise ValueError(f"apply_fillet(R{radius}) failed: {e}")

    def apply_chamfer(self, obj, size, edge_names=None, direction=None, z_level=None):
        """Chamfer edges."""
        if not edge_names:
            edge_names = self.select_edges(obj, direction=direction, z_level=z_level)
        if not edge_names:
            logger.warning(f"apply_chamfer({size}): no edges")
            return obj

        try:
            edges = []
            for name in edge_names:
                idx = int(name.replace("Edge", "")) - 1
                if 0 <= idx < len(obj.Shape.Edges):
                    edges.append(obj.Shape.Edges[idx])

            if not edges:
                return obj

            new_shape = obj.Shape.makeChamfer(size, edges)
            if new_shape.isNull():
                raise ValueError(f"makeChamfer({size}) returned null")

            chamfer = self.doc.addObject("Part::Feature", f"Chamfer_{obj.Name}")
            chamfer.Shape = new_shape
            self.doc.recompute()
            return self._validate(chamfer, "apply_chamfer")

        except Exception as e:
            raise ValueError(f"apply_chamfer({size}) failed: {e}")

    # ==========================================================================
    # BOOLEAN OPERATIONS
    # ==========================================================================

    def cut_objects(self, base, tool):
        """Boolean subtraction: base - tool."""
        try:
            cut = self.doc.addObject("Part::Cut", f"Cut_{base.Name}")
            cut.Base = base
            cut.Tool = tool
            cut.Refine = True
            self.doc.recompute()
            return self._validate(cut, "cut_objects")
        except Exception as e:
            raise ValueError(f"cut_objects failed: {e}")

    def fuse_objects(self, objects):
        """Boolean union. Falls back to compound for non-intersecting bodies."""
        if not objects:
            raise ValueError("fuse_objects: empty list")
        if len(objects) == 1:
            return objects[0]

        logger.info(f"fuse_objects: {len(objects)} objects")

        try:
            fuse = self.doc.addObject("Part::MultiFuse", "Fusion")
            fuse.Shapes = objects
            fuse.Refine = True
            self.doc.recompute()
            
            # Check if fusion produced valid geometry
            if fuse.Shape.isNull() or fuse.Shape.Volume < 0.001:
                raise ValueError("Fusion result is null or empty")
            
            # CUT-THROAT FIX: Ensure single solid result
            if len(fuse.Shape.Solids) > 1:
                raise ValueError("Fusion created disjoint solids (parts DO NOT intersect). Move parts closer.")

            return self._validate(fuse, "fuse_objects")
        except Exception as e:
            # CUT-THROAT FIX: No compound fallback. 
            # If fusion fails, the geometry is invalid for manufacturing.
            raise ValueError(f"fuse_objects failed: {e} (Ensure objects intersect and are valid solids)")

    def intersect_objects(self, objects):
        """Boolean intersection."""
        if len(objects) < 2:
            return objects[0] if objects else None

        try:
            common = self.doc.addObject("Part::MultiCommon", "Intersection")
            common.Shapes = objects
            common.Refine = True
            self.doc.recompute()
            return self._validate(common, "intersect_objects")
        except Exception as e:
            raise ValueError(f"intersect_objects failed: {e}")

    # ==========================================================================
    # EXPORT
    # ==========================================================================

    def export_step(self, obj, file_path):
        import Import
        self._safe_path(file_path)
        self._validate(obj, "export_step input")

        if not obj.Shape.isValid():
            logger.warning("Shape invalid, attempting kernel fix...")
            obj.Shape.fix(0.01, 0.01, 0.01)
            if not obj.Shape.isValid():
                # CUT-THROAT FIX: Do not ship broken geometry.
                raise ValueError("Export Failed: Geometry is invalid (non-manifold or self-intersecting) and could not be healed.")

        Import.export([obj], file_path)

        if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
            raise ValueError(f"STEP export failed: {file_path}")
        logger.info(f"Exported: {file_path}")

    def export_stl(self, obj, file_path, tolerance=0.05):
        self._safe_path(file_path)
        self._validate(obj, "export_stl input")
        
        # CUT-THROAT FIX: Strict pre-tessellation check
        if not obj.Shape.isValid():
             logger.warning("Shape invalid, attempting kernel fix...")
             obj.Shape.fix(0.01, 0.01, 0.01)
             if not obj.Shape.isValid():
                 raise ValueError("Export Failed: Geometry is invalid (non-manifold or self-intersecting).")

        mesh_obj = self.doc.addObject("Mesh::Feature", "ExportMesh")
        mesh_obj.Mesh = Mesh.Mesh(obj.Shape.tessellate(tolerance))
        mesh_obj.Mesh.write(file_path)

        if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
            raise ValueError(f"STL export failed: {file_path}")
        logger.info(f"Exported: {file_path}")

    # ==========================================================================
    # ADVANCED (Helix, Sweep - stubs for future)
    # ==========================================================================

    def create_helix(self, name, pitch, height, radius, radius2=None):
        """Helical path for threads/springs."""
        helix = self.doc.addObject("Part::Helix", name)
        helix.Pitch = pitch
        helix.Height = height
        helix.Radius = radius
        if radius2:
            helix.Radius2 = radius2
        self.doc.recompute()
        return helix

    # ==========================================================================
    # INTROSPECTION TOOLS (For Self-Correction)
    # ==========================================================================

    def get_bounding_box(self, obj):
        """Returns dict with bbox dimensions and center."""
        if not hasattr(obj, 'Shape') or obj.Shape.isNull():
            raise ValueError("Cannot get bbox of null shape")
        bb = obj.Shape.BoundBox
        return {
            'min': (bb.XMin, bb.YMin, bb.ZMin),
            'max': (bb.XMax, bb.YMax, bb.ZMax),
            'center': (bb.Center.x, bb.Center.y, bb.Center.z),
            'size': (bb.XLength, bb.YLength, bb.ZLength),
            'volume': obj.Shape.Volume
        }

    def measure_distance(self, obj1, obj2):
        """Returns minimum distance between two objects."""
        if not hasattr(obj1, 'Shape') or not hasattr(obj2, 'Shape'):
             raise ValueError("Objects must have shapes")
        return obj1.Shape.distToShape(obj2.Shape)[0]

    def check_volume(self, obj):
        """Returns volume, raises error if zero."""
        if not hasattr(obj, 'Shape') or obj.Shape.isNull():
             raise ValueError("Null shape")
        vol = obj.Shape.Volume
        if vol <= 0.000001:
             raise ValueError(f"Object {obj.Name} has zero volume")
        return vol

    # ==========================================================================
    # ATOMIC OPERATIONS (The "LEGO Blocks")
    # ==========================================================================

    def create_sketch(self, name, plane='XY', offset=0):
        """Creates a sketch on a standard plane."""
        # Note: Actual sketch geometry population usually requires 
        # complex constraint solving. For now, we return empty sketch.
        # Ideally, this would take a list of (x,y) points.
        # This is placeholder for future strict sketching.
        sketch = self.doc.addObject('Sketcher::SketchObject', name)
        # Set placement...
        return sketch

    def extrude_profile(self, name, sketch_or_face, distance, symmetric=False):
        """Extrudes a sketch or face into a solid."""
        # This replaces the need for "Part.extrude" manual calls
        extrude = self.doc.addObject("Part::Extrusion", name)
        extrude.Base = sketch_or_face
        extrude.Dir = Base.Vector(0, 0, distance)
        extrude.Solid = True
        extrude.Symmetric = symmetric
        self.doc.recompute()
        return self._validate(extrude, "extrude_profile")

    def revolve_profile(self, name, sketch_or_face, axis_dir, angle=360):
        """Revolves a profile around an axis."""
        revolve = self.doc.addObject("Part::Revolution", name)
        revolve.Source = sketch_or_face
        revolve.Axis = axis_dir # tuple (x,y,z) or Vector
        revolve.Angle = angle
        revolve.Solid = True
        self.doc.recompute()
        return self._validate(revolve, "revolve_profile")

    def loft_profiles(self, name, profiles, solid=True, ruled=False):
        """Lofts through multiple sketches/faces."""
        loft = self.doc.addObject("Part::Loft", name)
        loft.Sections = profiles
        loft.Solid = solid
        loft.Ruled = ruled
        self.doc.recompute()
        return self._validate(loft, "loft_profiles")
