"""INSTRUCTIONS
Run "autogrip.py" in Blender's text editor or install it as an add-on through the preferences menu. 
Once that's done, check object mode, and all the buttons you need are in a tab in the N-panel called 
"AutoGrip."

With the armature you want to use selected, you can pick which type of rig it is from the drop-down.
Formats supported so far are MakeHuman Exchange, Rigify, and Auto-Rig Pro. 

If it's not a model you made and you're not 100% sure, you can use "Guess Rig Type" to quickly
 compare its hand setup to the ones this program can handle.

Click "setup" to assemble both hands, or just "Setup Right" or "Setup Left" if you don't need both
(or your model doesn't have both).

It'll take about 20-30 seconds, during which a lot of my debug notes will print in the system 
console. Let that finish, and you'll have a tangle of small needley bones sticking off the hands, 
but the pose won't change yet. (If you don't seem to have the small needley bones, check the 
tooltip for the rig type you chose and make sure you can actually see the layer where it left them.)

The influence of the contraints depends on the rotation of the control bones - those are the longer
ones that stick out from the knuckles. If they're at rest, pointing out from the back of the hand, 
it's 0%. If they're rotated 90 degrees on the local X axis, so they jab forward over the fingers 
like Wolverine claws, it's 100%.

"Quick Pose" puts all of those to 90 degrees, and takes a guess at where the opposable thumbs should 
be positioned. The hands should now be fists, but the thumb positions often need a bit of manual 
(hah) tweaking in pose mode.

If you select another mesh object, then select the armature again so armature is active, you'll 
have options for "Grip Target R" and "Grip Target L." These actually set the targets of the 
constraints to that other mesh you have selected, so the hand can grab on properly. You can also 
set a different target later without having to run the initial setup again.

I'm going to add more options to fine-tune the "collision" results, but most of the time, the 
control bones will have all you need. Scaling them affects the offset of the shrinkwrap constraints
 and can help with a bit of clipping.

If you're sick of it and you want your old armature back, "Reset Hand R" and "Reset Hand L" clean up
after themselves pretty well, deleting everything this script did and leaving the original rig
untouched.
"""


bl_info = {
    "name": "AutoGrip",
    "blender": (3, 3, 0),
    "category": "Object",
    "description": "Automatically poses hands to grab props."
}

import bpy
from bpy import context
import mathutils
import numpy as np
import math

# I put this prefix on all the constraints and such I make with this add-on,
# so that they're easy to locate and remove on a reset
prefix = "AutoGrip_"


makehuman_dictionary = {
        
    "palm_index.L": ["f_index.01.L", "f_index.02.L", "f_index.03.L"],
    "palm_middle.L": ["f_middle.01.L", "f_middle.02.L", "f_middle.03.L"],
    "palm_ring.L": ["f_ring.01.L", "f_ring.02.L", "f_ring.03.L"],
    "palm_pinky.L": ["f_pinky.01.L", "f_pinky.02.L", "f_pinky.03.L"],
        
    "palm_index.R": ["f_index.01.R", "f_index.02.R", "f_index.03.R"],
    "palm_middle.R": ["f_middle.01.R", "f_middle.02.R", "f_middle.03.R"],
    "palm_ring.R": ["f_ring.01.R", "f_ring.02.R", "f_ring.03.R"],
    "palm_pinky.R": ["f_pinky.01.R", "f_pinky.02.R", "f_pinky.03.R"],
        
        
    "thumb.01.L": ["thumb.02.L", "thumb.03.L"],
    "thumb.01.R": ["thumb.02.R", "thumb.03.R"]
}
    
rigify_dictionary = {
    "ORG-palm.01.L": ["f_index.01.L", "f_index.02.L", "f_index.03.L"],
    "ORG-palm.02.L": ["f_middle.01.L", "f_middle.02.L", "f_middle.03.L"],
    "ORG-palm.03.L": ["f_ring.01.L", "f_ring.02.L", "f_ring.03.L"],
    "ORG-palm.04.L": ["f_pinky.01.L", "f_pinky.02.L", "f_pinky.03.L"],
        
    "ORG-palm.01.R": ["f_index.01.R", "f_index.02.R", "f_index.02.R"],
    "ORG-palm.02.R": ["f_middle.01.R", "f_middle.02.R", "f_middle.02.R"],
    "ORG-palm.03.R": ["f_ring.01.R", "f_ring.02.R", "f_ring.03.R"],
    "ORG-palm.04.R": ["f_pinky.01.R", "f_pinky.02.R", "f_pinky.03.R"],
        
    "ORG-thumb.01.L": ["thumb.02.L", "thumb.03.L"],
    "ORG-thumb.01.R": ["thumb.02.R", "thumb.03.R"]
}
    
autorig_dictionary = {
    'c_index1_base.l': ['c_index1.l', 'c_index2.l', 'c_index3.l'],        
    'c_middle1_base.l': ['c_middle1.l', 'c_middle2.l', 'c_middle3.l'],        
    'c_ring1_base.l': ['c_ring1.l', 'c_ring2.l', 'c_ring3.l'],
    'c_pinky1_base.l': ['c_pinky1.l', 'c_pinky2.l', 'c_pinky3.l'],        
    'c_thumb1.l': ['c_thumb2.l', 'c_thumb3.l'],
        
    'c_index1_base.r': ['c_index1.r', 'c_index2.r', 'c_index3.r'],
    'c_middle1_base.r': ['c_middle1.r', 'c_middle2.r', 'c_middle3.r'],    
    'c_ring1_base.r': ['c_ring1.r', 'c_ring2.r', 'c_ring3.r'],        
    'c_pinky1_base.r': ['c_pinky1.r', 'c_pinky2.r', 'c_pinky3.r'],
    'c_thumb1.r': ['c_thumb2.r', 'c_thumb3.r'],
}

class fingerchain:
    phalanges = []
    control_bone = None
    axis = ''
    offset = 0.0
    projectors = [] 
    
    palmroot = None
    name = ''
    
    prop = None
    control_layer = 29
    project_layer = 30
    
    def __init__(self, boneslist, axis='x', name="Default", offset = 0.0):   # Use X as bend axis by default, unless
                                               # set otherwise on initiation
        print("Finger created")
        self.phalanges = boneslist
        self.axis = axis
        self.offset = offset
        self.palmroot = boneslist[0].parent
        self.name = name
        self.control_bone = None
        
        self.projectors = []
    
    def setup(self):    # Setup: calls the functions to create projectors, 
            # put IK constraints between phalanges and
                        # those projectors, and create control bone
        print("Setting up finger " + self.name)
        self.create_projectors()    
        self.constrain_IK()
        self.create_control()
    
    def view(self):
        print("\nFinger named " +self.name + ", of length " + str(len(self.phalanges)) + 
        ", starting bone " + self.phalanges[0].name, end = '')
        if self.axis!='':
            print(", axis = " + self.axis, end='')
        print(", root bone: " + self.palmroot.name)
        if len(self.projectors) > 0:
            print("Projectors: ")  
            for p in self.projectors[:]:
                print(p.name)
        else:
            print("No projectors established")
        if self.control_bone is None:
            print("No control bone established")
        else:
            print("Control bone is " + self.control_bone.name)
        if self.prop == None:
            print("No grip target established")
        else:
            print("Grip target: " + self.prop.name)
        print()
        
    def viewchain(self):
        print("bonechain of finger " + self.name)
        for f in self.phalanges:
            print(f.name, end=' ')
        print()
        
    def create_control(self):    
        # Creates control bone, does not rig up constraints for it
        
        # If it creates the control bones and tries to parent them to the hand when
        # the model is in a pose, they end up offset. Still function correctly,
        # but I'm putting it to rest position real quick to avoid that.
        prev_position = activeArmature.pose_position
        activeArmature.pose_position = 'REST'
        
        print("Creating control bone for finger " + self.name)
        
        palmroot_tail_loc = self.palmroot.tail       
        palmroot_name = self.palmroot.name
        #print("palmroot name is " + palmroot_name)
        
        postfix = palmroot_name[-1]
        
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        ebs = obj.data.edit_bones
        
        control = ebs.new("control_" + self.name + '.' + postfix)
        
        control.head = palmroot_tail_loc
        
        singlebone = self.palmroot
        axis = self.axis
        #print(axis)
        
        if type(axis) is str:
            #print("axis is string")
            if axis == '-x': 
                translation = singlebone.x_axis 
            elif axis == '-y':
                translation = singlebone.y_axis
            elif axis == '-z':
                translation = singlebone.z_axis
            elif axis == 'x':
                translation = - singlebone.x_axis 
            elif axis == 'y':
                translation = - singlebone.y_axis
            elif axis == 'z':
                translation = - singlebone.z_axis
        else:
            print("no valid control axis found")
            translation = (0.0, 0.0, 0.0)
            
        # It may be worth repeating the vector math to apply finger offset to this
    
        translation.length = singlebone.length  
        
        loc = control.head + mathutils.Vector(translation)

        control.tail = loc
        
        control.parent = name_to_editbone(self.palmroot.name)
        
        control.use_deform = False
        
        control.align_roll(self.palmroot.y_axis)
        
        stringholder = control.name
        
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        self.control_bone = name_to_posebone(stringholder)
        
        activeArmature.pose_position = prev_position
        
    def create_projectors(self):    
        # Creates projectors, does not set up constraints
         # Calls new_single_projector for each one
        print("creating projectors for finger " + self.name)
        
        created_list = []
        
        chain = self.phalanges
        palmroot = self.palmroot
        
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        ebs = obj.data.edit_bones
        
        editchain = []
        
        for posebone in chain[:]:
            namematch = name_to_editbone(posebone.name)
            editchain.append(namematch)
            
        """
    print("full editbones chain: ")
        for printbone in editchain[:]:
            print(printbone.name, end=' ')
        print()
    """
        
        #print("looping projector creation")
        for phalange in editchain[:]:
            created_list.append(self.new_single_projector(ebs, phalange))
        
        nameslist = []
        for i in created_list:
            nameslist.append(i.name)
        
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                
        for newprojector in nameslist:
            posematch = name_to_posebone(newprojector)
            self.projectors.append(posematch)
            #print(newprojector + " added to " + self.name + " projectors list")
            
    def new_single_projector(self, editbones, singlebone):     
        #Creates a single projector off a
        # single phalange bone
        #Singlebone needs to be editbone
        
        axis = self.axis
        
        #print("creating projector off bone " + singlebone.name)
        first = editbones.new("projector_" + singlebone.name)
        
        if type(axis) is str:
            #print('axis is string')
            if axis == '-x':
                translation = - singlebone.x_axis 
            elif axis == '-y':
                translation = - singlebone.y_axis
            elif axis == '-z':
                translation = - singlebone.z_axis
            elif axis == 'x':
                translation = singlebone.x_axis 
            elif axis == 'y':
                translation = singlebone.y_axis
            elif axis == 'z':
                translation = singlebone.z_axis
        else:
            print("no valid finger axis found")
            translation = (0.0, 0.0, 0.0)
        
        if self.offset != 0:
            print(self.name + " has a set offset of " + str(self.offset) + " radians")
            translation = rotate_around(translation, singlebone.y_axis, self.offset)
            
        translation.length = singlebone.length  
        #print(translation) 
        
        loc = singlebone.head + mathutils.Vector(translation)
        #print(first.name + " loc: " + str(loc))
        first.head = loc
        first.tail = singlebone.tail
        first.parent = singlebone.parent
        first.length = first.length / 3
        first.use_deform = False
        
        return first
                
    def damped_track_projectors(self):   
        #Adds damped track modifiers to each projector, 
        # attaching them to the corresponding phalange
        
        print("adding damped track modifiers")
        for j in self.phalanges:
            for p in self.projectors:
                if j.name in p:
                    #print("projector " + p.name + " to fingerbone " + j.name)
                    fingertiplock = p.constraints.new("DAMPED_TRACK")
                    fingertiplock.target = obj
                    fingertiplock.subtarget = j.name
                    fingertiplock.head_tail = 1.0
                    fingertiplock.name = prefix + "Damped Track"
                    
    def add_shrinkwraps(self):
        # This creates shrinkwrap constraints on each projector, but DOESN'T set the target yet
        # Looks for the shrinkwrap modifier and then calls  create_single_shrinkwrap if not found
        print("creating shrinkwrap constraints for " + self.name)
        
        #self.prop = griptarget
        
        for q in self.projectors:
            found = False
            for c in q.constraints:
                #print(c.name)
                if 'hrinkwrap' in c.name:
                    found = True
                    break
            if not found:   
                create_single_shrinkwrap(q)
    
    def target_shrinkwraps(self, griptarget):
        
        # Sets the target of the shrinkwrap constraints to the target object
        
        for p in self.projectors:
            for c in p.constraints:
                if 'hrinkwrap' in c.name:
                    c.target = griptarget
    
        
    def constrain_IK(self):
        
        # Adds IK constraints to each phalange, linking them to the corresponding projector
        # Calls addIK with phalange and projector
        
        print("Linking IK constraints for finger " + self.name)
        
        for joint in self.phalanges:
            namestring = "projector_" + joint.name
            aim = obj.pose.bones[namestring]
            addIK(joint, aim)
                
    def clean_layers(self):
        
        # Moves all the project bones and the control bone to designated layers.
    # You'd expect this to take an input, but I defined that out in 
    # set_armature_layers instead. May rearrange that for some clarity
        
        for joint in self.projectors:
            i = 0
            joint.bone.layers[self.project_layer] = True
            # Doing this in a weird order bc it won't let me set all layers to false
            while (i < 32):
                if self.project_layer != i:
                    joint.bone.layers[i] = False
                i = i+1
        i = 0
        self.control_bone.bone.layers[self.control_layer] = True
        while (i<32):
            if self.control_layer != i:
                self.control_bone.bone.layers[i] = False
            i = i+1
    
    def set_armature_layers(self):
        
        rig_choice = bpy.props.EnumProperty(
            name="Rig selection",
            description="Select an option",
            
            items = [ 
                ('MHX', "MHX", "MakeHuman Exchange"),
                ('RFY', "Rigify", "Modular armature from the Rigify add-on"),
                ('ARP', "AutoRig Pro", "Auto rig pro"),
            ]
        )
    
        rig_choice = obj.global_rig_choice
        
        if rig_choice == 'MHX':
            if self.control_bone.name[-1] == 'R':
                print("setting layer for RIGHT finger")
                self.control_layer = 22
            elif self.control_bone.name[-1] == 'L':
                print("setting layer for LEFT finger")
                self.control_layer = 6
            self.project_layer = 24
        elif rig_choice == 'RFY':
            self.control_layer = 6
            self.project_layer = 23
        elif rig_choice == 'ARP':
            self.control_layer = 16
            self.project_layer = 16
        self.clean_layers()
            
    def reconstruct(self):
        # When the finger already has a bonechain, finds projectors and control bone
        
        direction_char = self.palmroot.name[-1]
        
        print("Reconstructing finger " + self.name)
        
        if len(self.projectors) == 0:
            print("Relocate projectors:", end=' ')
            for i in self.palmroot.children_recursive:
                if "project" in i.name:
                    self.projectors.append(i)
            print(str(len(self.projectors)) + " projectors found")
        else:
            print((str(len(self.projectors))) + " projectors already linked")
            
        if self.control_bone == None:
            print("relocate control")
            stringcontrol = "control_" + self.name + '.' + direction_char
            try: 
                self.control_bone = obj.pose.bones[stringcontrol]
                print("found control bone, name " + self.control_bone.name)
                #break
            except:
                print("No control bone found for " + self.name)
                
        else:
            print("control bone already exists, name " + self.control_bone.name)
    
# These are honestly unnecessary but I thought I needed them at one point. Will clean it up
# to remove them later because they're literally one line
    
def name_to_editbone(key):
    return obj.data.edit_bones[key]
def name_to_bone(key):
    return obj.data.bones[key]
def name_to_posebone(key):
    return obj.pose.bones[key]
    
    
def rotation_matrix(axis, theta):
    #This is from here https://stackoverflow.com/questions/6802577/rotation-of-3d-vector
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])

def rotate_around(source, rotationaxis, offset):
    
    # Calls rotation_matrix in a way that's useful to me
    
    arr = np.dot(rotation_matrix(rotationaxis, offset), source)
    vector_arr = mathutils.Vector(tuple(arr))
    return vector_arr    

def addIK(posebone, target):
    
    #Hooks the designated posebone up with an IK constraint to the designated target,
    #with chain count set to 1 and iterations to 16 to keep down memory issues
    
    #print("adding IK to bone " + posebone.name)
    newIK = posebone.constraints.new("IK")
    newIK.chain_count = 1
    newIK.iterations = 16
    newIK.name = prefix + "IK"
    
    if type(posebone) == bpy.types.PoseBone:
        newIK.target = obj
        newIK.subtarget = target.name
    elif type(posebone) == bpy.types.Object:
        newIK.target = target

def create_single_shrinkwrap(projectorbone):
    
    # This adds the shrinkwrap constraints onto a pose bone, 
    # which should be a projector
    
    if type(projectorbone) is not bpy.types.PoseBone:
        print("!!! " + projectorbone.name + " is not pose bone")
        return
    newProject = projectorbone.constraints.new("SHRINKWRAP")
    newProject.shrinkwrap_type = "PROJECT"
    newProject.project_axis = "POS_Y"
    newProject.cull_face = "FRONT"    
    newProject.wrap_mode = "OUTSIDE_SURFACE"
    newProject.name = prefix + "shrinkwrap"
    
    #setting distance relative to bone length for the moment. Not perfect but it will do
    newProject.distance = 0.15 * projectorbone.length 
        
def assemble_hand(handbone):
    
    # Puts likely finger bones together in chains, 
    # then makes basic fingers out of them. Most of the rewriting to let this work on 
    # other armatures happens here.
     
    # Returns a list of fingers
    
    rig_choice = bpy.props.EnumProperty(
        name="Rig selection",
        description="Select an option",
        
        items = [ 
            ('MHX', "MHX", "MakeHuman Exchange"),
            ('RFY', "Rigify", "Modular armature from the Rigify add-on"),
            ('ARP', "AutoRig Pro", "Auto rig pro"),
            ('GUESS', "Best Guess", "Any armature this doesn't explicitly support. Unreliable"),
        ]
    )
    
    rig_choice = obj.global_rig_choice
    
    fingerlist = []
    fingerroots = []
    
    print("Assembling hand off of " + handbone.name + ", with rig choice " + rig_choice)
    
    chosen_dictionary = {}
    
    if rig_choice == 'MHX':
        chosen_dictionary = makehuman_dictionary
    elif rig_choice == "RFY":
        chosen_dictionary = rigify_dictionary
    elif rig_choice == "ARP":
        chosen_dictionary = autorig_dictionary
        
    print("choice = " + rig_choice)
    direction = handbone.name[-1]
    
    
    for key in chosen_dictionary:
        if key[-1] == direction:
            print("# " + key)
            fingerroots.append(obj.pose.bones[key])     
            
    # And then THIS assembles the fingers off each palm. I've got a dictionary set up 
    # that tells it the whole list of fingers it should be looking for for 
    # each rig type. Elegant? No. Fast? Yes
    
    # Now that I've got all 3 options using a dictionary, I should probably
    # merge more of these into one function
    
    for loop_palm in fingerroots:
        try:
            print()
            bonechain = []
            
            nameslist = chosen_dictionary[loop_palm.name]

            for j in nameslist:
                print(j, end=', ')
                bonechain.append(obj.pose.bones[j])
                
            if rig_choice == 'ARP':
                rootname = loop_palm.name
                fingername = rootname.split('_')[1]
                fingername = fingername[:-1]
            else:
                fingername = bonechain[0].basename
                
            
            if 'thumb' in fingername:
                if rig_choice == 'MHX':
                    if bonechain[0].name == "thumb.02.L":
                        print("\nCREATING LEFT MAKEHUMAN THUMB")
                        newfinger = fingerchain(bonechain, 'z', fingername, 0.8)
                    elif bonechain[0].name ==  "thumb.02.R":
                        print("\nCREATING RIGHT MAKEHUMAN THUMB")
                        newfinger = fingerchain(bonechain, 'z', fingername, -0.8)
                elif rig_choice == 'RFY':
                    if bonechain[0].name == "thumb.02.L":
                        print("\nCREATING LEFT RIGIFY THUMB")
                        newfinger = fingerchain(bonechain, 'z', fingername, -0.7)
                    elif bonechain[0].name ==  "thumb.02.R":
                        print("\nCREATING RIGHT RIGIFY THUMB")
                        newfinger = fingerchain(bonechain, 'z', fingername, 0.7)
                elif rig_choice == 'ARP':
                    print("\nCREATING AUTORIG THUMB")
                    newfinger = fingerchain(bonechain, '-z', fingername)
                    
            else:
                print("creating other finger")
                if rig_choice == 'ARP':
                    newfinger = fingerchain(bonechain, '-z', fingername)
                else:
                    newfinger = fingerchain(bonechain, 'z', fingername)
            
            fingerlist.append(newfinger)
        except:
            print("\n",aloop_palm.name, "FINGER NOT FOUND.")
        
    return fingerlist

def control_drivers(finger):
    
    # Puts rotation limits on control bone, then hooks up the influence of all those IK constraints
    # to depend on control bone rotation. Maybe the rotation limit part should be somewhere else
    
    finger.control_bone.rotation_mode = "XYZ"
    
    print("\nApplying rotation limits to " + finger.name + " control bone")
    rotationlock = finger.control_bone.constraints.new("LIMIT_ROTATION")
    rotationlock.owner_space = "LOCAL"
    rotationlock.name = prefix + "Rotation Limit"
    rotationlock.use_limit_x = True
    rotationlock.max_x = 3.14159 / 2
    rotationlock.use_limit_y = True
    rotationlock.use_limit_z = True
    
    print("Applying angle drivers")
    for joint in finger.phalanges:
        #print('driver for bone ' + joint.name)
        driver = obj.driver_add('pose.bones["' + joint.name + '"].constraints["' + prefix + 'IK"].influence').driver 
        v = driver.variables.new()
        v.name = 'gripcontrol'
        
        v.targets[0].id        = obj
        v.targets[0].data_path = 'pose.bones["' + finger.control_bone.name + '"].rotation_euler[0]'
        
        driver.expression = v.name + " * 0.637"
        
    print("Applying scale drivers")
    for p in finger.projectors:
        #print(p.name)
        stringholder = p.name
        scaledriver = obj.driver_add('pose.bones["' + stringholder + '"].constraints["' + prefix 
        + 'shrinkwrap"].distance').driver
        v = scaledriver.variables.new()
        v.name = 'gripscale'
        
        v.targets[0].id = obj
        v.targets[0].data_path = 'pose.bones["' + finger.control_bone.name + '"].scale[0]'
        
        scaledriver.expression = v.name + " * 0.005"

def find_hand_root(direction):
    
    rig_choice = bpy.props.EnumProperty(
        name="Rig selection",
        description="Select an option",
        
        items = [ 
            ('MHX', "MHX", "MakeHuman Exchange"),
            ('RFY', "Rigify", "Modular armature from the Rigify add-on"),
            ('ARP', "AutoRig Pro", "Auto rig pro"),
            ('GUESS', "Best Guess", "Any armature this doesn't explicitly support. Unreliable"),
        ]
    )
    
    rig_choice = obj.global_rig_choice
    
    try:
        if rig_choice == 'MHX':
            if direction.lower() == 'l':
                return obj.pose.bones['hand0.L']
            elif direction.lower() == 'r':
                return obj.pose.bones['hand0.R']
        elif rig_choice == 'RFY':
            if direction.lower() == 'l':
                return obj.pose.bones['DEF-hand.L']
            elif direction.lower() == 'r':
                return obj.pose.bones['DEF-hand.R']
        elif rig_choice == 'ARP':
            if direction.lower() == 'r':
                return obj.pose.bones['hand.r']
            elif direction.lower() == 'l':
                return obj.pose.bones['hand.l']
    except:
        # I'm trying to figure out how to report a more elegant error to the user if they're
        # on the wrong rig, without them needing to have open a console view. This is
        # not ideal but it'll take more research.
        
        raise RuntimeError("Couldn't find hand root. Are you sure you have the right rig type?")

def setup_hand(targetroot):
    
    # Takes a root hand bone, calls assemble_hand to get a list of fingers out of it
    # Then runs setup(), damped_track_projectors(), control_drivers(), and add_shrinkwraps()
    # on each one
    
    # Needs to run control_drivers after add_shrinkwraps
    
    fingers_list = assemble_hand(targetroot)
         
    for finger in fingers_list:
        finger.setup()
        finger.damped_track_projectors()
        finger.add_shrinkwraps()
        control_drivers(finger)
        finger.set_armature_layers()

class AutoGripSetup(bpy.types.Operator):
    """Set up AutoGrip rig"""
    bl_idname = "object.autogrip_setup"
    bl_label = "AutoGrip Setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("\n~~~~~~~~~~~START~~~~~~~~~~~~\n")

        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        print("skeleton is " + activeArmature.name)
            
        lefthandroot = find_hand_root('L')
        righthandroot = find_hand_root('R')
        
        r = l = True
        
        # There's gotta be a more elegant way to handle this setup, but I'm not
        # seeing it at the moment, so I'll come back. TODO
        
        if (prefix + 'hand_L') in activeArmature:
            if activeArmature[(prefix + 'hand_L')] == True:
                print("Left hand already set up.")
                l = False
                
        if (prefix + 'hand_R') in activeArmature:
            if activeArmature[(prefix + 'hand_R')] == True:
                print("Right hand already set up.")
                r = False
        
        if l:
            setup_hand(lefthandroot)
            activeArmature[(prefix + 'hand_L')] = True
        if r: 
            setup_hand(righthandroot)
            activeArmature[(prefix + 'hand_R')] = True
        

        return {'FINISHED'}
            
            
class AutoGripLeft(bpy.types.Operator):
    """Set up AutoGrip rig for left hand only"""
    bl_idname = "object.autogrip_setup_left"
    bl_label = "Setup Left"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("\n~~~~~~~~~~~START~~~~~~~~~~~~\n")
        
        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        
        print("skeleton is " + activeArmature.name)
        
        if (prefix + 'hand_L') in activeArmature:
            if activeArmature[(prefix + 'hand_L')] == True:
                print("Left hand already set up.")
                return {'FINISHED'}
            
        # I'm gonna wrap this up better into a find_handroot function
        
        lefthandroot = find_hand_root('l')
        
        setup_hand(lefthandroot)
        
        activeArmature[(prefix + 'hand_L')] = True
        
        return {'FINISHED'}
    

            
class AutoGripRight(bpy.types.Operator):
    """Set up AutoGrip rig for right hand only"""
    bl_idname = "object.autogrip_setup_right"
    bl_label = "Setup Right"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("\n~~~~~~~~~~~START~~~~~~~~~~~~\n")
        
        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        print("skeleton is " + activeArmature.name)
        
        if (prefix + 'hand_R') in activeArmature:
            if activeArmature[(prefix + 'hand_R')] == True:
                print("Right hand already set up.")
                return {'FINISHED'}

        righthandroot = find_hand_root('r')
        
        setup_hand(righthandroot)
        
        activeArmature[(prefix + 'hand_R')] = True
        
        return {'FINISHED'}
            
class TargetLeft(bpy.types.Operator):
    """Set Grip Target for left hand"""
    bl_idname = "object.autogrip_target_l"
    bl_label = "Grip Target L"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        #print(obj.name)
        
        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        print("skeleton is " + activeArmature.name)
        
        target = None

        lefthandroot = find_hand_root('L')

        for t in bpy.context.selected_objects:
            if t != obj:
                target = t
                break
        print("Grip target is " + target.name)
        
        left_hand_list = assemble_hand(lefthandroot)
        
        for i in left_hand_list:
            i.reconstruct()
            print("set target for left hand finger " + i.name)
            i.target_shrinkwraps(target)
        
        return {'FINISHED'}
    
class TargetRight(bpy.types.Operator):
    """Set Grip Target for right hand"""
    bl_idname = "object.autogrip_target_r"
    bl_label = "Grip Target R"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        #print(obj.name)
        
        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        print("skeleton is " + activeArmature.name)
        
        target = None

        righthandroot = find_hand_root('R')

        for t in bpy.context.selected_objects:
            if t != obj:
                target = t
                break
        print("Grip target is " + target.name)
        
        right_hand_list = assemble_hand(righthandroot)
        
        for i in right_hand_list:
            i.reconstruct()
            print("set target for right hand finger " + i.name)
            i.target_shrinkwraps(target)
        
        return {'FINISHED'}


def reset_hand(wristroot):
    
    scene = context.scene
    global obj 
    obj = bpy.context.active_object
    
    global activeArmature
    activeArmature = obj.data
    
    fingers_list = assemble_hand(wristroot)
    for f in fingers_list:
        f.reconstruct()
    
    print("removing constraints")
    
    for f in fingers_list:
            for p in f.phalanges:
                for c in p.constraints:
                    if prefix in c.name:
                        """drivercurves = c.influence.drivers
                        for d in drivercurves:
                            drivercurves.remove(drivercurves[0])"""
                        obj.driver_remove('pose.bones["' + p.name + '"].constraints["' + c.name + '"].influence')
                        # Exception may be thrown here if bone does not have constraint
                        p.constraints.remove(c)   
            for j in f.projectors:
                for c in j.constraints:
                    if prefix in c.name:
                        obj.driver_remove('pose.bones["' + j.name + '"].constraints["' + c.name + '"].distance')
                        # Exception may be thrown if bone does not have constraint
                        # No point in removing the constraint because I'll delete the whole bone
                        
    print('entering edit mode')
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    
    ebs = activeArmature.edit_bones
    
    print("deleting projectors")
    for f in fingers_list:
        for j in f.projectors:
            try:
                projectorname = j.name
                ebs.remove(ebs[projectorname])
            except:
                print("!!! failed to delete " + j.name)
        
    print("deleting control bones")
    for f in fingers_list:
        if f.control_bone == None:
            print(f.name + " has no control bone")
            continue
        try:
            controlname = f.control_bone.name
            ebs.remove(ebs[controlname])
        except:
            print("!!! failed to delete " + f.control_bone.name)
    
    print('entering object mode')
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)       
    
class ResetHandLeft(bpy.types.Operator):
    """Reset all autogrip stuff on left hand"""
    bl_idname = "object.autogrip_reset_l"
    bl_label = "Reset Hand L"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        print("resetting left hand")
        
        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        
        lefthandroot  = find_hand_root('L')
        
        print("left hand is " + lefthandroot.name)
        
        reset_hand(lefthandroot)
        
        activeArmature[(prefix + 'hand_L')] = False
        
        return {'FINISHED'}
    
class ResetHandRight(bpy.types.Operator):
    """Reset all autogrip stuff on right hand"""
    bl_idname = "object.autogrip_reset_r"
    bl_label = "Reset Hand R"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        print("resetting right hand")
        
        scene = context.scene
        global obj 
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        
        #righthandroot = obj.pose.bones['hand0.R']
        righthandroot = find_hand_root('R')
        
        print("right hand is " + righthandroot.name)
        
        reset_hand(righthandroot)
        
        activeArmature[(prefix + 'hand_R')] = False
        
        return {'FINISHED'}
    
class QuickPose(bpy.types.Operator):
    """Quickly put all control bones to active position"""
    bl_idname = "object.autogrip_quickpose"
    bl_label = "Quick Pose"
    bl_options = {'REGISTER', 'UNDO'}
    
    rig_choice = bpy.props.EnumProperty(
        name="Rig selection",
        description="Select an option",
        
        items = [ 
            ('MHX', "MHX", "MakeHuman Exchange"),
            ('RFY', "Rigify", "Modular armature from the Rigify add-on"),
            ('ARP', "AutoRig Pro", "Auto rig pro"),
            ('GUESS', "Best Guess", "Any armature this doesn't explicitly support. Unreliable"),
        ]
    )
    
    # This here is also depending on rig choice! Be wary
    
    def execute(self, context):
        print("Quickpose")
        
        pi = 3.14159
        
        scene = context.scene
        global obj
        obj = bpy.context.active_object
        
        global activeArmature
        activeArmature = bpy.context.active_object.data
        
        rig_choice = obj.global_rig_choice
        
        if ((prefix + 'hand_L') in activeArmature) and (activeArmature[(prefix + 'hand_L')]):
            #if activeArmature[(prefix + 'hand_L')] == True:
             #   print('hand actually set up')
            
            print("left hand set up")
            lefthandroot = find_hand_root('L')
            
            for bone in lefthandroot.children_recursive:
                if 'control' in bone.name:
                    bone.rotation_euler[0] = pi/2 
                    continue
                if rig_choice == 'MHX':
                    if 'thumb.01.L' in bone.name:
                        
                        print("quickpose mhx thumb LEFT")
                            # Set this to only affect axes that are not locked!
                        bone.rotation_euler[0] = 0.43
                        bone.rotation_euler[1] = 0.27
                        bone.rotation_euler[2] = 0.32
                                  
                elif rig_choice == 'RFY':
                    if 'ORG-thumb.01' in bone.name:
                        print("quickpose rigify thumb LEFT")
                        bone.rotation_quaternion[0] = 0.85
                        bone.rotation_quaternion[1] = -0.114
                        bone.rotation_quaternion[2] = 0.36
                        bone.rotation_quaternion[3] = 0.36
                        
                elif rig_choice == 'ARP':
                    if bone.name == 'c_thumb1_base.l':
                        print("quickpose autorig pro thumb LEFT")
                    
                        bone.rotation_euler[0] = 1.62
                        bone.rotation_euler[1] = 0
                        bone.rotation_euler[2] = -0.3
                    
        else:
            print('left hand not set up')
            
            
        if ((prefix + 'hand_R') in activeArmature) and (activeArmature[(prefix + 'hand_R')] == True):
        
            print('right hand set up')            
            righthandroot = find_hand_root('R')
            
            for bone in righthandroot.children_recursive:
                if 'control' in bone.name:
                    bone.rotation_euler[0] = pi/2
                    continue
                
                if rig_choice == 'MHX':
                    if 'thumb.01.R' in bone.name: 
                        print("quickpose mhx thumb RIGHT")
                        bone.rotation_euler[0] = 0.43
                        bone.rotation_euler[1] = -0.27
                        bone.rotation_euler[2] = -0.17
                                  
                elif rig_choice == 'RFY':
                    if 'ORG-thumb.01' in bone.name:
                        print("quickpose rigify thumb RIGHT")
                        bone.rotation_quaternion[0] = 0.85
                        bone.rotation_quaternion[1] = -0.114
                        bone.rotation_quaternion[2] = -0.36
                        bone.rotation_quaternion[3] = -0.36
                        
                elif rig_choice == 'ARP':
                    
                    if bone.name == 'c_thumb1_base.r':
                        print("quickpose autorig pro thumb RIGHT")
                    
                        bone.rotation_euler[0] = 1.62
                        bone.rotation_euler[1] = -0
                        bone.rotation_euler[2] = 0.3
        else:
            print('right hand not set up')
            
        return {'FINISHED'}
        
class github_link(bpy.types.Operator):
    
    """Check this out for updates or to report any issues you find"""
    bl_idname = "object.autogrip_discussion_link"
    bl_label = "Github Link"
    
    def execute(self, context):
        
        import webbrowser
        import imp
        webbrowser.open("https://github.com/Jetpack-Crow/autogrip")  
        
        return {'FINISHED'}
    
class kofi_link(bpy.types.Operator):
    
    """Donate a dollar or two?"""
    bl_idname = "object.kofi_link"
    bl_label = "Tip Jar"
    
    def execute(self, context):
        
        import webbrowser
        import imp
        webbrowser.open("https://ko-fi.com/jetpackcrow")  
        
        return {'FINISHED'}
    
def bone_in_armature(key):  # This function is used only for rig guessing.
    try:
        print(obj.pose.bones[key].name, "found in armature")
        return True
    except:
        print(key + " not found in armature")
        return False

class guess_rig_type(bpy.types.Operator):
    """Check if rig is compatible with any of the precoded types."""
    
    bl_idname = "object.autogrip_guess_rig"
    bl_label = "Guess Rig Type"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        
        scene = context.scene
        global obj
        obj = bpy.context.active_object
        global activeArmature
        activeArmature = bpy.context.active_object.data
        
        print("guessing rig type for", obj.name)
        
        dictionaries_list = [makehuman_dictionary, rigify_dictionary, autorig_dictionary]
        type_names_list = ['MHX', 'RFY', 'ARP']
        
        rig_type = None
        
        message = "Rig doesn't match precoded types."
        
        for type in dictionaries_list:
            match = True
            
            # There has to be a better way to get the corresponding name than this.
            # But it's what I got for now. TODO
            
            dictionary_index = dictionaries_list.index(type)
            
            rig_type = type_names_list[dictionary_index]
            
            for key in type:
                if bone_in_armature(key):
                    continue
                else:
                    print("Armature cannot be " + rig_type)
                    match = False
                    break
            if match:
                
                obj.global_rig_choice = rig_type
                
                message = "Rig type: " + rig_type
                break
        
        self.report({'INFO'}, message)
    
        return {'FINISHED'}

        
class PANEL_PT_Autogrip(bpy.types.Panel):
    """Creates a sub tab in the N-panel"""
    bl_label = "AutoGrip Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AutoGrip"
    #bl_context = "objectmode"
    
    def draw(self, context):
        global obj
        obj = context.active_object 
        
        global activeArmature
        activeArmature = obj.data
        
        target = None
        for t in bpy.context.selected_objects:
            if t != obj and type(t.data) is bpy.types.Mesh:
                target = t
                break
        
        layout = self.layout
        
        """Provide setup options only if armature selected, provide target options only
        if there is a valid target to attach them to."""
        
        if type(activeArmature) is bpy.types.Armature:
            
            row = layout.row()
            row.label(text="Active armature: {}".format(activeArmature.name))
            
            row = layout.row()
            #row.label(text = "enum choice")
            row.prop(obj, "global_rig_choice")
            
            row = layout.row()
            row.operator(guess_rig_type.bl_idname)
            
            row = layout.row()
            
            row = layout.row()
            row.operator(AutoGripSetup.bl_idname)
            
            setuprow = layout.row()
            setupright = setuprow.operator(AutoGripRight.bl_idname)
            setupleft = setuprow.operator(AutoGripLeft.bl_idname)
            
            QProw = layout.row()
            QProw.operator(QuickPose.bl_idname)
            
            resetrow = layout.row()
            resetrow.operator(ResetHandRight.bl_idname)
            resetrow.operator(ResetHandLeft.bl_idname)
            
            if (target is not None) and (type(target.data) is bpy.types.Mesh):
                row = layout.row()
                row.label(text = "Target object: {}".format(target.name))
                
                row = layout.row()
                row.operator(TargetRight.bl_idname)
                row.operator(TargetLeft.bl_idname)
        else:
            row = layout.row()
            row.label(text = "No armature active.")   
            
            row = layout.row()
            row.label(text="Links (Open in browser)")
            
            row = layout.row()
            row.operator(github_link.bl_idname)
            row.operator(kofi_link.bl_idname)
                       
        
classes = [AutoGripSetup, AutoGripLeft, AutoGripRight, TargetRight, TargetLeft,
    ResetHandLeft, ResetHandRight, QuickPose, PANEL_PT_Autogrip, github_link, guess_rig_type,
    kofi_link]        
        
def register():
    
    # This just iterates over all the classes I defined and sets each one up, 
    # then creates the global_rig_choice enum that I'm gonna need. A rough copy of that
    # is also defined in each other function that needs it because "global" isn't as 
    # elegant as you would think here.
    
    print('\n~~~~~~~~~~~~registering setup~~~~~~~~~~~~\n')
    
    for item in classes:
        bpy.utils.register_class(item)
    
    bpy.types.Object.global_rig_choice = bpy.props.EnumProperty(
        name="Rig selection",
        description="Select an option",
        
        items = [ 
            ('MHX', "MHX", "MakeHuman Exchange\n" + 
            "Puts control bones on layers 7 and 23 for Fingers" +
            "\nPuts projectors on layer 24"),
            ('RFY', "Rigify", "Modular armature from the Rigify add-on.\n" + 
            "Puts control bones on layer 6 for Fingers (Detail)\n" + 
            "Puts projectors on layer 23"),
            ('ARP', "Auto-Rig Pro", "Armature from the Auto-Rig Pro add-on.\n" + 
            "Puts control bones and projectors on layer 16")
            #('GUESS', "Best Guess", "This will do its best to reconstruct some hands from\n" + 
            #"any given armature. Not implemented yet"),
        ]
    )


def unregister():
    
    for item in classes:
        bpy.utils.unregister_class(item)
        
    del bpy.types.Object.global_rig_choice
    
    
if __name__ == "__main__":
    register()
    #unregister()