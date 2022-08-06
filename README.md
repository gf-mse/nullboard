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

#### 

<!-- 

(1)
 - (host A -> stash remote)
 - (host B <- fetch )
 - // continue on host B

(2)
 - ... host A continues to update an old board, creating a fork
 - (host B -> stash remote)
 - (host A: stash local and fetch remote)
 - (host A: merge stashed)
 - // host A: review the merge, continue ...

-->

<!------------------------------------------------------------>

[apankrat-nb]: https://github.com/apankrat/nullboard
[apankrat-nb-issue-57]: https://github.com/apankrat/nullboard/issues/57#issuecomment-1125926959
[ofryl-nodejs-bk]: https://github.com/OfryL/nullboard-nodejs-agent
[apankrat-nb-4jag]: https://github.com/apankrat/nullboard/issues/54#issuecomment-1139188206
[nb-poc-commit-f790731c96]: https://github.com/gf-mse/nullboard/commit/f790731c96d77b2183d2a3973ecd8b1ca866c321
