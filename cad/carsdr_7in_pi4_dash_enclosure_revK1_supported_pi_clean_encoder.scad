
// REV K.1 NOTES
// - Move rear lid screw blocks out of encoder bay.
// - Add visible support columns/webs under Pi shelf.
// - Intended as structural cleanup pass before adding more features.

/*
  CarSDR 7-inch Raspberry Pi Touchscreen + Raspberry Pi 4 Dash Enclosure
  REV J - clean hardware-measured rebuild

  Baseline known measurements:
  - Existing SmartiPi-style body: 220 x 115 x 25 mm
  - Display metal back plate: 190 x 115 x 3 mm
  - Display mount hole centers, relative to display upper-left:
      X = 60 mm and 186 mm
      Y = 25 mm and 92 mm
    => spacing: 126 mm x 67 mm

  Rev J design strategy:
  - Use real 4-point display mounting, not clamp rails
  - Add left encoder wing for 3x KY-040 modules
  - Keep rear shell simple and serviceable
  - Single rear cover
  - Rear/bottom cable exit for RJ45, USB, USB-C, GPIO
  - Simple strong hinge interface
  - No internal VESA posts, no mystery panels, no floating nonsense

  Units: millimeters

  Coordinate system:
  - X increases left-to-right in front view
  - Y increases bottom-to-top in front view
  - Z increases rearward into the case
  - Front face is Z=0
*/

$fn = 64;

// -----------------------------------------------------------------------------
// Core dimensions
// -----------------------------------------------------------------------------

wall = 3;
corner_r = 7;

// SmartiPi-style main display body.
smart_body_w = 220;
smart_body_h = 115;
smart_body_d = 25;

// Added control wing.
wing_w = 62;

// Overall front shell.
case_w = smart_body_w + wing_w;
case_h = smart_body_h;
case_d = 54;  // deeper than SmartiPi to allow Pi4, cables, and rear service room

// Display metal back plate.
display_w = 190;
display_h = 115;
display_t = 3;

// Place display area inside main display body, to the right of encoder wing.
// SmartiPi shell is 220 wide; display is 190 wide, leaving ~15mm each side.
display_x = wing_w + 15;
display_y = 0;

// Visible window estimate. Tweak if screen opening needs adjustment.
window_w = 156;
window_h = 88;
window_x = display_x + (display_w - window_w)/2;
window_y = display_y + (display_h - window_h)/2;

// Front recess around screen.
recess_w = 184;
recess_h = 106;
recess_x = display_x + (display_w - recess_w)/2;
recess_y = display_y + (display_h - recess_h)/2;

// Display mounting holes measured from display upper-left in user coordinates.
// User gave Y from top, but OpenSCAD Y starts at bottom, so convert:
// y_openscad = display_y + display_h - y_from_top.
display_mount_x1 = display_x + 60;
display_mount_x2 = display_x + 186;
display_mount_y_top = display_y + display_h - 25;
display_mount_y_bottom = display_y + display_h - 92;

// Display mount post geometry.
display_post_d = 9;
display_post_h = 10;
display_screw_d = 3.2;       // M3 clearance-ish
display_insert_d = 4.8;      // optional M3 heat-set pocket
display_insert_h = 5;

// Pi4 mounting, high-left/rear-ish inside main body.
// This is still adjustable, because the Pi4 port/cable shell is reality's little prank.
pi_w = 85;
pi_h = 56;
pi_mount_dx = 58;
pi_mount_dy = 49;
pi_hole_d = 2.8;             // M2.5 clearance
pi_standoff_d = 7;
pi_standoff_h = 8;

pi_x = wing_w + 35;
pi_y = case_h - 76;
pi_z = 31;                   // behind display mount frame/board area
pi_shelf_pad = 8;
pi_shelf_t = 3;

// Encoders.
encoder_x = wing_w/2;
encoder_spacing = 34;
encoder_top_y = case_h/2 + encoder_spacing;

encoder_hole_d = 7.4;
encoder_recess_d = 15;
encoder_recess_h = 2;
encoder_board_w = 34;
encoder_board_h = 23;
encoder_board_depth = 18;

label_size = 7.8;
label_depth = 0.8;
label_drop = 13;

// Rear cover.
lid_margin = 7;
lid_t = 3;
lid_screw_d = 3.4;
lid_pilot_d = 2.7;
insert_d = 4.8;
insert_h = 5;

// Rear lid screw locations.
// Rev K.1: keep these out of the encoder bay so they do not look like
// random rotary-encoder mounting tabs. Left screw column starts just to the
// right of the encoder/display divider.
lid_mount_left_x   = wing_w + 14;
lid_mount_right_x  = case_w - lid_margin - 12;
lid_mount_bottom_y = lid_margin + 12;
lid_mount_top_y    = case_h - lid_margin - 12;

// Rear/bottom cable bay.
cable_bay_w = 126;
cable_bay_h = 32;
cable_bay_x = wing_w + 70;
cable_bay_y = 7;
cable_bay_z = case_d - wall - 1;

// Fan.
fan_center_x = case_w - 48;
fan_center_y = 42;
fan_d = 24;
fan_hole_spacing = 24;

// Hinge / stand.
hinge_tab_w = 86;
hinge_tab_h = 34;
hinge_tab_t = 13;
hinge_hole_d = 5.4;          // M5 clearance
hinge_x = wing_w + smart_body_w/2 - hinge_tab_w/2;
hinge_y = -hinge_tab_h + 3;
hinge_z = case_d - 24;

stand_w = 165;
stand_h = 90;
stand_t = 5;

// Expansion blank area on rear lid.
exp_w = 60;
exp_h = 36;
exp_x = case_w - exp_w - 16;
exp_y = case_h - exp_h - 14;

// -----------------------------------------------------------------------------
// Utility modules
// -----------------------------------------------------------------------------

module rr(w,h,r) {
    hull() {
        translate([r,r]) circle(r=r);
        translate([w-r,r]) circle(r=r);
        translate([r,h-r]) circle(r=r);
        translate([w-r,h-r]) circle(r=r);
    }
}

module rb(w,h,d,r) {
    linear_extrude(height=d) rr(w,h,r);
}

module screw_post(x,y,z,h,od,id,insert=false) {
    translate([x,y,z])
        difference() {
            cylinder(h=h,d=od);

            translate([0,0,-0.3])
                cylinder(h=h+0.6,d=id);

            if (insert)
                translate([0,0,h-insert_h])
                    cylinder(h=insert_h+0.3,d=display_insert_d);
        }
}

module label(txt) {
    translate([0,0,-label_depth])
        linear_extrude(height=label_depth)
            text(txt,
                 size=label_size,
                 font="Liberation Sans:style=Bold",
                 halign="center",
                 valign="center");
}

// -----------------------------------------------------------------------------
// Main cutouts
// -----------------------------------------------------------------------------

module front_screen_cutouts() {
    // Shallow display recess.
    translate([recess_x,recess_y,-3])
        rb(recess_w,recess_h,wall+5,4);

    // Actual visible window.
    translate([window_x,window_y,-4])
        rb(window_w,window_h,wall+8,3);
}

module rear_cavity_cutout() {
    // Main rear cavity.
    translate([lid_margin,lid_margin,wall])
        rb(case_w - 2*lid_margin,
           case_h - 2*lid_margin,
           case_d,
           5);

    // Encoder bay hollow.
    translate([7,8,wall])
        rb(wing_w - 14,
           case_h - 16,
           case_d,
           4);
}

module encoder_cutouts() {
    for (i=[0:2]) {
        y = encoder_top_y - i*encoder_spacing;

        // shaft hole
        translate([encoder_x,y,-4])
            cylinder(h=wall+8,d=encoder_hole_d);

        // front nut/washer recess
        translate([encoder_x,y,-encoder_recess_h])
            cylinder(h=encoder_recess_h+0.3,d=encoder_recess_d);

        // KY-040 board pocket
        translate([encoder_x - encoder_board_w/2,
                   y - encoder_board_h/2,
                   wall])
            cube([encoder_board_w,encoder_board_h,encoder_board_depth]);
    }
}

module encoder_wire_tunnel() {
    // Big through-tunnel from encoder bay to main cavity.
    translate([wing_w-3,case_h/2-35,14])
        cube([30,70,case_d-10]);
}

module cable_bay_cutout() {
    // Rear lower opening.
    translate([cable_bay_x,cable_bay_y,cable_bay_z])
        rb(cable_bay_w,cable_bay_h,wall+6,4);

    // Interior scoop.
    translate([cable_bay_x-12,cable_bay_y-2,case_d-28])
        cube([cable_bay_w+24,cable_bay_h+4,32]);
}

module fan_cutouts() {
    translate([fan_center_x,fan_center_y,case_d-wall-0.5])
        cylinder(h=wall+1,d=fan_d);

    for (sx=[-1,1]) for (sy=[-1,1]) {
        translate([fan_center_x+sx*fan_hole_spacing/2,
                   fan_center_y+sy*fan_hole_spacing/2,
                   case_d-wall-0.5])
            cylinder(h=wall+1,d=3);
    }
}

module rear_vents() {
    for (i=[0:11]) {
        translate([wing_w+46+i*8,case_h-28,case_d-wall-0.5])
            rb(4,18,wall+1,2);
    }
}

// -----------------------------------------------------------------------------
// Re-added structure
// -----------------------------------------------------------------------------

module display_mount_posts() {
    /*
      Rev J.2:
      Dedicated display mounting frame.

      Screen mount holes are explicitly placed in two vertical columns:
        left column  = display_x + 60
        right column = display_x + 186

      and two rows:
        top row    = display_y + display_h - 25
        bottom row = display_y + display_h - 92

      This should make visual inspection sane, which is apparently too much to ask
      from previous geometry.
    */

    frame_d = display_post_h;
    rail_t = 12;
    side_t = 10;

    x_left  = display_mount_x1;
    x_right = display_mount_x2;
    y_top   = display_mount_y_top;
    y_bot   = display_mount_y_bottom;

    frame_x = x_left - 18;
    frame_y = y_bot - 18;
    frame_w = (x_right - x_left) + 36;
    frame_h = (y_top - y_bot) + 36;

    difference() {
        union() {
            // Top rail
            translate([frame_x, y_top - rail_t/2, wall])
                rb(frame_w, rail_t, frame_d, 3);

            // Bottom rail
            translate([frame_x, y_bot - rail_t/2, wall])
                rb(frame_w, rail_t, frame_d, 3);

            // Left vertical rail
            translate([x_left - side_t/2, frame_y, wall])
                rb(side_t, frame_h, frame_d, 3);

            // Right vertical rail
            translate([x_right - side_t/2, frame_y, wall])
                rb(side_t, frame_h, frame_d, 3);

            // Larger pads around the exact screen screw locations
            translate([x_left - 8,  y_top - 8, wall]) rb(16,16,frame_d,3);
            translate([x_right - 8, y_top - 8, wall]) rb(16,16,frame_d,3);
            translate([x_left - 8,  y_bot - 8, wall]) rb(16,16,frame_d,3);
            translate([x_right - 8, y_bot - 8, wall]) rb(16,16,frame_d,3);
        }

        // Exact screen mounting holes
        translate([x_left,  y_top, -0.3]) cylinder(h=frame_d+wall+1,d=display_screw_d);
        translate([x_right, y_top, -0.3]) cylinder(h=frame_d+wall+1,d=display_screw_d);
        translate([x_left,  y_bot, -0.3]) cylinder(h=frame_d+wall+1,d=display_screw_d);
        translate([x_right, y_bot, -0.3]) cylinder(h=frame_d+wall+1,d=display_screw_d);

        // Optional heat-set insert pockets from rear side
        translate([x_left,  y_top, frame_d-display_insert_h+wall])
            cylinder(h=display_insert_h+0.6,d=display_insert_d);

        translate([x_right, y_top, frame_d-display_insert_h+wall])
            cylinder(h=display_insert_h+0.6,d=display_insert_d);

        translate([x_left,  y_bot, frame_d-display_insert_h+wall])
            cylinder(h=display_insert_h+0.6,d=display_insert_d);

        translate([x_right, y_bot, frame_d-display_insert_h+wall])
            cylinder(h=display_insert_h+0.6,d=display_insert_d);
    }

    // Thin display alignment ledges, separate from screw-hole frame.
    ledge_t = 3;
    ledge_d = 4;

    translate([display_x+4,display_y+4,wall])
        cube([display_w-8,ledge_t,ledge_d]);

    translate([display_x+4,display_y+display_h-ledge_t-4,wall])
        cube([display_w-8,ledge_t,ledge_d]);

    translate([display_x+4,display_y+4,wall])
        cube([ledge_t,display_h-8,ledge_d]);

    translate([display_x+display_w-ledge_t-4,display_y+4,wall])
        cube([ledge_t,display_h-8,ledge_d]);
}

module pi_shelf_and_standoffs() {
    shelf_x = pi_x - pi_shelf_pad;
    shelf_y = pi_y - pi_shelf_pad;
    shelf_w = pi_w + 2*pi_shelf_pad;
    shelf_h = pi_h + 2*pi_shelf_pad;

    /*
      Rev K.1:
      The Pi shelf is now visibly supported from the front-floor plane instead
      of hovering in the case like it has discovered antigravity. The shelf still
      sits behind the display hardware, but it has four support legs and side webs.
    */

    // Main Pi shelf.
    translate([shelf_x,shelf_y,pi_z])
        rb(shelf_w,shelf_h,pi_shelf_t,4);

    // Four support legs from front/floor plane up to underside of Pi shelf.
    leg_w = 8;
    leg_h = pi_z - wall;

    translate([shelf_x, shelf_y, wall])
        cube([leg_w, leg_w, leg_h]);

    translate([shelf_x + shelf_w - leg_w, shelf_y, wall])
        cube([leg_w, leg_w, leg_h]);

    translate([shelf_x, shelf_y + shelf_h - leg_w, wall])
        cube([leg_w, leg_w, leg_h]);

    translate([shelf_x + shelf_w - leg_w, shelf_y + shelf_h - leg_w, wall])
        cube([leg_w, leg_w, leg_h]);

    // Long side webs under the shelf for stiffness.
    web_t = 3;
    translate([shelf_x, shelf_y, wall])
        cube([shelf_w, web_t, leg_h]);

    translate([shelf_x, shelf_y + shelf_h - web_t, wall])
        cube([shelf_w, web_t, leg_h]);

    // Short front/back webs.
    translate([shelf_x, shelf_y, wall])
        cube([web_t, shelf_h, leg_h]);

    translate([shelf_x + shelf_w - web_t, shelf_y, wall])
        cube([web_t, shelf_h, leg_h]);

    // Top stiffening ribs on the shelf.
    translate([shelf_x,shelf_y,pi_z])
        cube([shelf_w,3,13]);

    translate([shelf_x,shelf_y+shelf_h-3,pi_z])
        cube([shelf_w,3,13]);

    translate([shelf_x,shelf_y,pi_z])
        cube([3,shelf_h,13]);

    translate([shelf_x+shelf_w-3,shelf_y,pi_z])
        cube([3,shelf_h,13]);

    // Exactly 4 Pi mount points.
    screw_post(pi_x,pi_y,pi_z+pi_shelf_t,pi_standoff_h,pi_standoff_d,pi_hole_d,false);
    screw_post(pi_x+pi_mount_dx,pi_y,pi_z+pi_shelf_t,pi_standoff_h,pi_standoff_d,pi_hole_d,false);
    screw_post(pi_x,pi_y+pi_mount_dy,pi_z+pi_shelf_t,pi_standoff_h,pi_standoff_d,pi_hole_d,false);
    screw_post(pi_x+pi_mount_dx,pi_y+pi_mount_dy,pi_z+pi_shelf_t,pi_standoff_h,pi_standoff_d,pi_hole_d,false);
}

module rear_lid_corner_blocks() {
    /*
      Rev K.1:
      Rear lid screw blocks moved out of the encoder bay. They are now in the
      main service area, so the encoder compartment stays clean.
    */
    block = 24;
    z = wall;

    translate([lid_mount_left_x - block/2, lid_mount_bottom_y - block/2, z])
        corner_block(block);

    translate([lid_mount_right_x - block/2, lid_mount_bottom_y - block/2, z])
        corner_block(block);

    translate([lid_mount_left_x - block/2, lid_mount_top_y - block/2, z])
        corner_block(block);

    translate([lid_mount_right_x - block/2, lid_mount_top_y - block/2, z])
        corner_block(block);
}

module corner_block(block) {
    difference() {
        rb(block,block,8,3);
        translate([block/2,block/2,-0.3])
            cylinder(h=8.6,d=lid_pilot_d);
        translate([block/2,block/2,8-insert_h])
            cylinder(h=insert_h+0.3,d=insert_d);
    }
}

module hinge_tab() {
    difference() {
        union() {
            translate([hinge_x,hinge_y,hinge_z])
                rb(hinge_tab_w,hinge_tab_h,hinge_tab_t,4);

            // strong web into rear wall
            translate([hinge_x+8,hinge_y+hinge_tab_h-2,hinge_z-18])
                cube([hinge_tab_w-16,6,28]);

            // gussets
            translate([hinge_x+8,hinge_y+5,hinge_z-18])
                rotate([90,0,0])
                    linear_extrude(height=6)
                        polygon([[0,0],[22,0],[22,30]]);

            translate([hinge_x+hinge_tab_w-30,hinge_y+5,hinge_z-18])
                rotate([90,0,0])
                    linear_extrude(height=6)
                        polygon([[0,0],[22,0],[0,30]]);
        }

        translate([hinge_x+hinge_tab_w/2,
                   hinge_y-2,
                   hinge_z+hinge_tab_t/2])
            rotate([-90,0,0])
                cylinder(h=hinge_tab_h+4,d=hinge_hole_d);
    }
}

module labels_and_divider() {
    translate([encoder_x,encoder_top_y-label_drop,0]) label("VOL");
    translate([encoder_x,encoder_top_y-encoder_spacing-label_drop,0]) label("MODE");
    translate([encoder_x,encoder_top_y-2*encoder_spacing-label_drop,0]) label("TUNE");

    translate([wing_w-1.2,6,-0.45])
        rb(2.4,case_h-12,1.1,1.2);
}

// -----------------------------------------------------------------------------
// Main shell
// -----------------------------------------------------------------------------

module front_shell_raw() {
    difference() {
        union() {
            rb(case_w,case_h,case_d,corner_r);

            // raised display surround
            translate([recess_x-5,recess_y-5,-1.2])
                rb(recess_w+10,recess_h+10,2.2,5);

            // raised encoder wing face
            translate([4,4,-0.7])
                rb(wing_w-8,case_h-8,1.4,6);
        }

        front_screen_cutouts();
        rear_cavity_cutout();
        encoder_cutouts();
        encoder_wire_tunnel();
        cable_bay_cutout();
        fan_cutouts();
        rear_vents();
    }

    display_mount_posts();
    pi_shelf_and_standoffs();
    rear_lid_corner_blocks();
    hinge_tab();
    labels_and_divider();
}

// -----------------------------------------------------------------------------
// Rear lid
// -----------------------------------------------------------------------------

module rear_lid_raw() {
    lid_w = case_w - 2*lid_margin - 2;
    lid_h = case_h - 2*lid_margin - 2;

    // Convert shell/global screw mount coordinates to rear-lid local coordinates.
    lid_local_left_x   = lid_mount_left_x  - lid_margin - 1;
    lid_local_right_x  = lid_mount_right_x - lid_margin - 1;
    lid_local_bottom_y = lid_mount_bottom_y - lid_margin - 1;
    lid_local_top_y    = lid_mount_top_y    - lid_margin - 1;

    difference() {
        rb(lid_w,lid_h,lid_t,4);

        // lid screws, aligned to moved screw blocks
        translate([lid_local_left_x,lid_local_bottom_y,-0.4])
            cylinder(h=lid_t+0.8,d=lid_screw_d);

        translate([lid_local_right_x,lid_local_bottom_y,-0.4])
            cylinder(h=lid_t+0.8,d=lid_screw_d);

        translate([lid_local_left_x,lid_local_top_y,-0.4])
            cylinder(h=lid_t+0.8,d=lid_screw_d);

        translate([lid_local_right_x,lid_local_top_y,-0.4])
            cylinder(h=lid_t+0.8,d=lid_screw_d);

        // cable bay notch
        translate([cable_bay_x-lid_margin-1,
                   cable_bay_y-lid_margin-1,
                   -0.4])
            rb(cable_bay_w+2,cable_bay_h+2,lid_t+0.8,4);

        // expansion blank area, just a rectangular cutout.
        translate([exp_x-lid_margin,
                   exp_y-lid_margin,
                   -0.4])
            rb(exp_w,exp_h,lid_t+0.8,4);

        // fan opening
        translate([fan_center_x-lid_margin-1,
                   fan_center_y-lid_margin-1,
                   -0.4])
            cylinder(h=lid_t+0.8,d=fan_d);

        // vents
        for(i=[0:13]) {
            translate([38+i*8,lid_h-28,-0.4])
                rb(4,18,lid_t+0.8,2);
        }
    }
}

module expansion_blank_raw() {
    difference() {
        rb(exp_w,exp_h,3,4);
        translate([8,8,-0.4]) cylinder(h=3.8,d=3.2);
        translate([exp_w-8,8,-0.4]) cylinder(h=3.8,d=3.2);
        translate([8,exp_h-8,-0.4]) cylinder(h=3.8,d=3.2);
        translate([exp_w-8,exp_h-8,-0.4]) cylinder(h=3.8,d=3.2);
    }
}

// -----------------------------------------------------------------------------
// Stand
// -----------------------------------------------------------------------------

module dash_stand_raw() {
    difference() {
        rb(stand_w,stand_h,stand_t,8);
        translate([22,18,-0.4]) rb(48,8,stand_t+0.8,3);
        translate([stand_w-70,18,-0.4]) rb(48,8,stand_t+0.8,3);
        translate([22,stand_h-28,-0.4]) rb(48,8,stand_t+0.8,3);
        translate([stand_w-70,stand_h-28,-0.4]) rb(48,8,stand_t+0.8,3);
    }

    cheek_t = 10;
    cheek_h = 54;
    cheek_d = 20;
    gap = hinge_tab_w + 8;

    translate([stand_w/2-gap/2-cheek_t,stand_h-20,stand_t])
        difference() {
            rb(cheek_t,cheek_d,cheek_h,2);
            translate([cheek_t/2,-1,34])
                rotate([-90,0,0])
                    cylinder(h=cheek_d+2,d=hinge_hole_d);
        }

    translate([stand_w/2+gap/2,stand_h-20,stand_t])
        difference() {
            rb(cheek_t,cheek_d,cheek_h,2);
            translate([cheek_t/2,-1,34])
                rotate([-90,0,0])
                    cylinder(h=cheek_d+2,d=hinge_hole_d);
        }
}

// -----------------------------------------------------------------------------
// Orientation / preview
// -----------------------------------------------------------------------------

module mirror_for_front_view() {
    translate([case_w,0,0])
        mirror([1,0,0])
            children();
}

module assembly_preview_raw() {
    front_shell_raw();

    translate([lid_margin+1,case_h+24,case_d+4])
        rear_lid_raw();

    translate([case_w-90,case_h+24,case_d+12])
        expansion_blank_raw();

    translate([wing_w+40,-108,0])
        dash_stand_raw();
}

module final_preview() {
    mirror_for_front_view()
        assembly_preview_raw();
}

final_preview();

// Export helpers:
// Comment final_preview() above and uncomment one:
//
// mirror_for_front_view() front_shell_raw();
// mirror_for_front_view() rear_lid_raw();
// mirror_for_front_view() dash_stand_raw();
// mirror_for_front_view() expansion_blank_raw();
//
// Raw orientation if needed:
// front_shell_raw();
// rear_lid_raw();
// dash_stand_raw();
// expansion_blank_raw();
