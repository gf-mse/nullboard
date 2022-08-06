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
