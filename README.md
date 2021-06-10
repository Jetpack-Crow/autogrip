# Autogrip

This is a helpful little tool for hand rigs that lets them automatically grab onto mesh props. 

# Tutorial

Run "autogrip.py" in Blender's text editor or install it as an add-on through the preferences menu. Once that's done, check object mode, and all the buttons you need are in a tab in the N-panel called "AutoGrippy."

With the armature you want to use selected, you can pick which type of rig it is from the drop-down. Formats supported so far are MakeHuman Exchange, Rigify, and Auto-Rig Pro. 

If it's not a model you made and you're not 100% sure, you can use "Guess Rig Type" to quickly compare its hand setup to the ones this program can handle.

Click "setup" to assemble both hands, or just "Setup Right" or "Setup Left" if you don't need both (or your model doesn't have both).

It'll take about 20-30 seconds, during which a lot of my debug notes will print in the system console. Let that finish, and you'll have a tangle of small needley bones sticking off the hands, but the pose won't change yet. 
(If you don't seem to have the small needley bones, check the tooltip for the rig type you chose and make sure you can actually see the layer where it left them.)

The influence of the contraints depends on the rotation of the control bones - those are the longer ones that stick out from the knuckles. If they're at rest, pointing out from the back of the hand, it's 0%. If they're rotated 90 degrees on their local X axis, so they jab forward over the fingers like Wolverine claws, it's 100%.

"Quick Pose" puts all of those to 90 degrees, and takes a guess at where the opposable thumbs should be positioned. The hands should now be fists, but the thumb positions often need a bit of manual (hah) tweaking in pose mode.

If you select another mesh object, then select the armature again so armature is active, you'll have options for "Grip Target R" and "Grip Target L." These actually set the targets of the constraints to that other mesh you have selected, so the hand can grab on properly. You can also set a different target later without having to run the initial setup again.

I'm going to add more options to fine-tune the "collision" results, but most of the time, the control bones will have all you need. Scaling them affects the offset of the shrinkwrap constraints and can help with a bit of clipping.

If you're sick of it and you want your old armature back, "Reset Hand R" and "Reset Hand L" clean up after themselves pretty well, deleting everything this script did and leaving the original rig untouched.