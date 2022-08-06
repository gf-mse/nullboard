# Nullboard POC

<!-- FILLME: add a TOC here -->

## Summary

This proof-of-concept project has several things in it:

 1. First, there is a Python-based [backup server](./nullboard-backup) for Alexander Pankratov' [Nullboard][apankrat-nb] project (see [nullboard-backup](./nullboard-backup/README.md) directory) ;
    * <sub> the goal here was to create something hackable _in Python_, so if you are after something more production-stable, you may want to look at other alternatives, e.g. [nullboard-nodejs-agent][apankrat-nb-issue-57] by [OfryL][ofryl-nodejs-bk] </sub>
 2. Second, there is a proof-of-concept [implementation](./nullboard) of merging board content for the same project (see below) ;
 3. Third, both (1) and (2) are slightly extended to support using the same board on multiple devices. This is based on [4jag's][apankrat-nb-4jag] approach and allows for two simple workflows -- a simple push/pull and pull/merge ; again, see below for details.

For a Python backup server description, go to [its own page ](./nullboard-backup/README.md).     
Board merging implementation is described below.

Please also read the [proof-of-concept warning](#proof-of-concept-warning).


## Merging NB Boards

The proposed workflow is that we "stash" a board to be merged to a temporary internal "register" slot, and then merge the "stashed" board with the current one:

![merging NB boards in action](doc/nullboard-demo-1.gif "merging nb boards using 'stash' / 'merge' operations")

### The Algorithm

The idea behind merging is quite simple and is borrowed from the way it is done in old-school editors like Emacs:

  * first, we assign each list and each note a unique id : this allows us to cheat and determine which notes or list titled have been changed )
  * second, if we don't know how to merge two texts, we just write them both side-by-side, or the new version on top of the old one.

Finally, after merging two boards, let us highlight "old", "new" and "merge conflict" note cells and let the user review and update the results.

( See the gif above for an illustration on how that might look like. )

### Notes on Implemetation

First and foremost -- sadly this is the first piece of JS code I ever wrote; I was trying to be sensible, but please be warned.

In particular, js code may have a few extra bits, since I did not immediately realise that JSON does not serialize function methods, and therefore we shall rather instead use the usual common functions applied to objects )

Otherwise, the merge algorithm is pretty straighforward:

  * (a) build an index (note id) -> (note data) for all notes ; if the index already has a note, merge the old and the new one, as described above
     * in particular, "note data" shall have the list id of the list where the note belonged )
  * (b) merge the list headers the same way (by making a quick (list id) -> (list) index), producing an array of new (empty) note lists
  * (c) go through the note index from (a), and put the (merged) note to a list with a list id of the original note

Finally, for a pair of boards to merge, let us voluntarily consider the second one to be the "new" version, and therefore give it some priority in the case of a conflict -- for example, if a note changed lists, let us put it after the merge in the "new" list instead of the "old" one.

That's about it; however -- to make things easier, I will quickly comment on commit history below.

#### proof-of-concept warning

Please expect this to be a proof-of-concept version: the code shall work, but may require some minor polishing.

For example, I did not update blob version code (shame on me); to update your "classic" board with id fields, do a dummy edit (e.g. press Ctrl-Enter twice to add an empty note and then delete it), but at the moment there is no pre-merge check that both boards have an "updated" format with all lists and notes having ids. Please add one or ping me to do so if you don't feel capable, but please know that this may take another six months or even longer from me to find a small time window. (See the thread in [issue 54][apankrat-nb-issue-54] to get an idea.)

However, all "old format" board shall in general be importable, and for any new boards this shall just work; finally, since any unknown fields shall in general just be ignored, any "new format" board shall in theory be easily importable back to the "classic" NB.

#### preparations

First, there are some minor cosmetic and development-mode changes:

  * adding board revision number to the exported filename: [9eb4ee7ca2][9eb4ee7ca2]
  * adding board id and revision number to nullboard page title: [a612a59b9c][a612a59b9c]

This shall make it a little easier to distinguish between various saves of the same board -- and between several imported versions of the same.

Also, there's now an option to overwrite the existing board with the same id on import: [982e26384f][982e26384f].

#### marked notes

[5e0f76cb72][5e0f76cb72] introduces a 'M' button in addition to "classic" 'X', 'R', '&#95;' ones, which shall toggle note's "marked" state, represented by magenta-ish background. ('M' will also meas "merged" later on.)

#### note and list ids

[0444e472f0][0444e472f0] adds unique ids for note and list entities. 

A standard approach for that would be to use uuids, but I was a little concerned about performance, so we keep using same id format as for NB boards -- that is, a JS timestamp.

One small problem with that is that while a board is supposed to be created by a human and therefore two board ids -- at least for a set of boards used by the same person -- are quite likely to be unique; with computer-generated objects, two notes or two lists can easily get the same millisecond timestamp, and so we need to cheat again: [IdGen][idgen-fn] object will generally use a random timestamp for a new id, unless that one has been used already, in which case it will keep incrementing the counter. After some time passes, it will be a new random timestamp again.

#### old and new notes

[776b2f1149][776b2f1149] introduces "old" ('O') and "new" ('N') note styles -- very much the same as [5e0f76cb72][5e0f76cb72] does for "marked" notes ('M'); the only remark to make here is that it the implementation is suboptimal, and of course these fields shall be implemented by a single `.style` field instead of separate boolean variables -- which would be a little clumsy for a prod, but shall be Ok for a proof-of-concept demo. I omitted that being in a bit of a hurry, please feel free to improve it if you feel like it.

#### stashing a board

[0ddc4c084d][0ddc4c084d] adds two new menu items: "stash" will make a local (deep) in-memory clone of the current board at a predefined temporary location, and "unstash" will replace the current board with the one extracted from there.

#### merge boards

[342e7946a8][342e7946a8] implements merging: first, we "stash" a board that we intend to merge to that temporary in-memory "variable", and next, we make another board active and can now _merge_ the two.

UI-wise, we have one another menu item for this, and there will be a keyboard shortcut added later.

As one note -- the "stashed" board is considered to be the "new" one and takes minor precedence -- for example, when deciding on a new position for a note that has changed lists.

#### a test board to play

To make testing easier, [41dcd0ec39][41dcd0ec39] adds a special menu item -- "make a test board", which does exactly that -- creates a very simple test board to practice with merging.

#### make it shared

Using a local "stashed" board means that we will have to export and import the boards that we would want to merge, which could be a little annoying.

Based on [4jag's approach][apankrat-nb-4jag], we'll be using a dedicated _remote_ location for the same -- which will require us to slightly extend our backup server by adding two more endpoints: `<remote>/stash-board` to "put the most recently used board on a shelf", so to speak -- and `<remote>/stash-board` to pick the most recently used board from that shelf.

So basically these are the same "stash"/"unstash" operations, just with a remote server.

[f790731c96][f790731c96] implements just that -- and one more thing, which is a combination of the above: "stash-and-fetch-remote", which is exactly as it says -- first, we "stash" the current board as described in a section above, and then we fetch the last "shelved" board from the remote and make it current.

After that, we can now review the remote version we just have fetched and can now merge it with the the one we have stashed locally.

#### suggested workflows

The above allows for two simple workflows -- a "push/pull" and "pull/merge" :

In "push/pull", we create a board on a host A, update it, then push ("shelve") it at remote, and continue on host B after pulling it.

In "pull/merge", we continue working on _the original version_ of the board on the host A, creating a version fork of our board; the most common reason for this could be forgetting to push to remote ("shelve") our most recent changes from host B, while we're back at host A.

However, if next time we won't forget to "shelve" our forked board changes from A to the remote location, we can merge them back into B when we are back there. For that, we first open the most recent _local_ version of the board on B, then do a "stash-and-fetch-remote", which pulls the most recent forked version from A, stashing the B version, and then invoke a "merge stashed" comamnd which will merge these two.

Now we shall review the changes, most of which (except for the board and list titles) will be color coded -- and we are done with the forks. (You can now push the result of the merge back to the remote -- or at least do it before leaving B, so you won't create another board fork again. But even if you do, it shall be no drama anymore ))


#### adding some hotkeys

Finding a menu item in the menu is not as irritating as a need to constantly do import/export of boards, but can still be a bit annoying if done too often -- so [6321efd72c][6321efd72c] adds a few hotkeys to assist with that:

  * First, `Alt-Shift-o|m|n` shortcuts, similar to `Alr-Shift-r` used to switch note "raw" mode, can be used to clear after-merge syntax highlighting (it does not happen automagically at first edit, since the author believes that it is more annoying to acidentally lose a mark on a note than to explicitly un-mark them once; your mileage may vary)
 
Next, a number of `Ctrl-Alt-Shift-` shortcuts for remote and merge operations:

  * `Ctrl-Alt-Shift-r` to send /"shelve"/ a board to a remote location (mnemonic: "rrr-remote") ;
  * `Ctrl-Alt-Shift-f` to fetch a "shelved" board from the <u>r</u>emote (mnemonic: "fetch", "from") ;
  * `Ctrl-Alt-?` (`Ctrl-Alt-Shift-/`) for a "stash-and-fetch" operation (mnemonic: there are two versions involved, "a" and "b" => "a/b")
  * `Ctrl-Alt-+` (`Ctrl-Alt-Shift-=`) for a "merge stashed" operation (mnemonic: a "+" for "merge")

#### protocols and such

Please refer to [nullboard-backup README file](./nullboard-backup/README.md) for a description of communication specifics between a Nullboard page and a Nullboard backup server.


<!------------------------------------------------------------>

[apankrat-nb]: https://github.com/apankrat/nullboard
[apankrat-nb-issue-54]: https://github.com/apankrat/nullboard/issues/54
[apankrat-nb-issue-57]: https://github.com/apankrat/nullboard/issues/57#issuecomment-1125926959
[ofryl-nodejs-bk]: https://github.com/OfryL/nullboard-nodejs-agent
[apankrat-nb-4jag]: https://github.com/apankrat/nullboard/issues/54#issuecomment-1139188206
[nb-poc-commit-f790731c96]: https://github.com/gf-mse/nullboard/commit/f790731c96d77b2183d2a3973ecd8b1ca866c321

[982e26384f]: https://github.com/gf-mse/nullboard/commit/982e26384f73b07cdd117dbebf80b1b551d78885
[9eb4ee7ca2]: https://github.com/gf-mse/nullboard/commit/9eb4ee7ca27a2202a7d8937db5c4a2ce4a5a3595
[a612a59b9c]: https://github.com/gf-mse/nullboard/commit/a612a59b9c880b86093c8444a45489e83d2f2cad
[5e0f76cb72]: https://github.com/gf-mse/nullboard/commit/5e0f76cb72b8b21a00ace50012f0f93d4b924103
[0444e472f0]: https://github.com/gf-mse/nullboard/commit/0444e472f08fde011bc38245979f4fa9ab4f4e88

[idgen-fn]: https://github.com/gf-mse/nullboard/blob/c31db5f2770290e6b219aad5d57e1a99fb200e1d/nullboard/nullboard.html#L2642

[776b2f1149]: https://github.com/gf-mse/nullboard/commit/776b2f11498a2cdc94fd73227caa1b63358ba015
[0ddc4c084d]: https://github.com/gf-mse/nullboard/commit/0ddc4c084dceda0bc0b1d5fbfb345ddae4378ada
[342e7946a8]: https://github.com/gf-mse/nullboard/commit/342e7946a8b4a44c1d9c4d86dca57c1b6fe4f9b4
[41dcd0ec39]: https://github.com/gf-mse/nullboard/commit/41dcd0ec391e49e3ee180c400723f3923d388830
[f790731c96]: https://github.com/gf-mse/nullboard/commit/f790731c96d77b2183d2a3973ecd8b1ca866c321
[6321efd72c]: https://github.com/gf-mse/nullboard/commit/6321efd72c2e827e8ec866312d29ae5e5a8adf28
