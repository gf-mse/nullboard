# nullboard-backup

This is a Flask-based implemenation for a backup server for for Alexander Pankratov' [Nullboard][apankrat-nb] project.

<!-- FILLME: add a TOC here -->

  * [A Fair Warning](#a-fair-warning)
  * [Prerequisites](#prerequisites)
  * Alternatives
  * Protocol Overview
  * Implementation Details

## A Fair Warning

First things first: this is a _working_ implementation, but the code could be a bit messy -- see [implementation details](#implementation-details) below.

One may want to use this for one of two main reasons:
  * (a) you want something hackable in Python that you can customize for your needs
  * (b) there is a [proof-of-concept Nullboard fork][nullboard-poc-dev] that allows to merge board revisions (as well as merging separate boards -- although it may not be that helpful), and you want a compatible version that supports send and fetch from remote.

## Prerequisites

There is a [prerequisites.sh](prerequisites.sh) script that will install them for you, but in fact there are only three:

  1. `flask`
  2. `flask-cors`
  3. `netifaces`

We would obviously need Flask, [Flask-CORS][flask-cors] is required to reply with a correct `Access-Control-Allow-Origin:` header (see the [protocol overview](#protocol-overview) section), and `netifaces` is a convenience-only dependency, which can be easily removed from the code.




<!------------------------------------------------------------>

[apankrat-nb]: https://github.com/apankrat/nullboard
[apankrat-nb-issue-54]: https://github.com/apankrat/nullboard/issues/54
[apankrat-nb-issue-57]: https://github.com/apankrat/nullboard/issues/57#issuecomment-1125926959
[ofryl-nodejs-bk]: https://github.com/OfryL/nullboard-nodejs-agent
[apankrat-nb-4jag]: https://github.com/apankrat/nullboard/issues/54#issuecomment-1139188206
[nb-poc-commit-f790731c96]: https://github.com/gf-mse/nullboard/commit/f790731c96d77b2183d2a3973ecd8b1ca866c321
[nullboard-poc-dev]: https://github.com/gf-mse/nullboard/tree/dev/
[flask-cors]: https://flask-cors.readthedocs.io/en/3.0.10/
