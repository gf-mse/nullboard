# nullboard-backup

This is a Flask-based implemenation for a backup server for for Alexander Pankratov' [Nullboard][apankrat-nb] project.

<!-- FILLME: add a TOC here -->

  * [A Fair Warning](#a-fair-warning)
  * [Prerequisites](#prerequisites)
  * [Alternatives](#alternatives)
  * [Protocol Overview](#protocol-overview)
    * [a http session example](#a-http-session-example)
    * [an informal specification](#an-informal-specification)
  * [Notes on Implementation](#notes-on-implementation)

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

## Alternatives

You may want to have a look at [nullboard-nodejs-agent][apankrat-nb-issue-57] by [OfryL][ofryl-nodejs-bk], and/or [nullboard-agent][nullboard-agent] -- the original backup server implemenation for Windows, written in C.


## Protocol Overview

I am going to describe my understanding of Nullboard backup protocol below. You can skip this section unless you want to roll out your own implementation, or would need to fix something -- for example, in the case if the protocol has changed and you want to understand the way it was.

### a http session example

Since I believe that most people would prefer an example to a specification -- here is a reduced `http` session example captured by Wireshark:

```
PUT /board/1659177201493 HTTP/1.1
Host: 127.0.0.1:20001
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0
Accept: application/json, text/javascript, */*; q=0.01
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Access-Token: 12345
Content-Length: 3456
Origin: null
Connection: keep-alive
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: cross-site

self=file%3A%2F%2F%2F...

Content-Type: text/html; charset=utf-8
Content-Length: 2
Access-Control-Allow-Origin: null
Vary: Origin
Server: Werkzeug/1.0.1 Python/3.6.9
Date: Tue, 02 Aug 2022 08:55:38 GMT

{}
```

I truncated the payload after `file%3A%2F%2F%2F` and replaced it with an ellipsis, but essentially it is a `www-form-urlencoded` json dictionary, which I will describe below.

### an informal specification

As we know, Nullboard has "local backup" and "remote backup" settings.

  1. "Local backup" expects a http server at `127.0.0.1:10001`.
  2. "Remote backup" server specification for the same would look as `http://127.0.0.1:10001` ; you get the idea.
  3. "Access token" value goes into `X-Access-Token:` header of the request ; e.g. the above session example uses access token value of "12345".
     * if you do not want to handle this token -- for example you assume that your network is safe enough (e.g. a localhost connection or a small vpn, etc), it can be ignored
  5. Our backup server shall support at least  'PUT', 'DELETE' and 'OPTIONS requests, although the latter two can be ignored (with an empty 200 reply -- see the code for details); for boards, the `put` request comes at `/board/<board-id>` url.
  6. The client sends an `Origin:` header with a value depending on the address of the Nullboard page, and expects a `Access-Control-Allow-Origin:` header in the reply; this response header shall either contain the same value as was sent in the `Origin:` field, or an asterisk `*`, or any other compatible value as specified by [the CORS standard][cors-protocol-spec].
     * My suggestion would be to go with mirroring of the same value, unless you know better.
  7. The client would send the payload encoded as `www-form-urlencoded`, although would expect the result to be plain json (`application/json`). Go figure. ( As a side note -- in my example the client receives a `text/html` mimetype in the response -- which I suppose fits an `*/*` spec -- but it seems to be happy as long as the payload parses as valid json. See also [notes on implementation](#notes-on-implementation) below. )
  8. When decoded, the content of the payload would be a json dictionary of the following form: `{ "data": <1>, "meta": <2>, "self": <3> }`, where `<1>` and `<2>` would be _stringified_ (i.e. further encoded, this time -- converted to a string form) versions of `json` dictionaries, and `<3>` would simply be the address of the Nullboard page as seen by the client.
     * `meta` (`<2>`) field content example: ` "{\"title\":\"test board\",\"current\":2,\"ui_spot\":0,\"history\":[2,1],\"backupStatus\":{\"simp-3\":{}}}"` -- as one can see, it can be decoded to the following json fragment: `{'title': 'test board', 'current': 2, 'ui_spot': 0, 'history': [2, 1], 'backupStatus': {'simp-3': {}}}`
     * `data` field would contain a _stringified_ version of our board as it would have been saved by Nullboard "Export this board" menu option.


## Notes on Implementation

I have started this trying to get _something working_, ideally -- in no time, since time was a bit of an issue; so I have picked Flask because some googling revealed that it might be a good choice for quickly powering up a REST API in Python. 

However, I have never used Flask before and the protocol details described above were yet to be discovered.

So the code started with a simple Flask "hello, world" app, then I tried to save _anything_ that is sent our way and only then started to extract and save the board data.

Finally, due to a certain lack of time, I have left "it as" is almost the first moment it started to do the job -- so the code inside is not exactly neat and is more like a product of a moderately chaotic evolution process.

Now let us get to some details.

### flask specifics - the form field

As one can see from the [http session](#a-http-session-example) section, our data is coming as an url-encoded payload of a `put` request; for reasons unknown, Flask [chooses to expose the parsed result][on-flask-data-fields] [as a `.form` field][flask-form-field] if it comes this way, and [as a `.json` field][flask-json-field] -- if it has a json-compatible mimetype (which apparently [does not include `text/javascript`][flask-is-json-2.2.x])

### no delete

Furthermore, from `put`, `options` and `delete` operations only `put` has an actual non-trivial implementation; in other words, the `delete` requests are effectively ignored. (This is not too hard to change and in fact there are commented lines in the code that do almost that -- renaming the saved boards to `filename.deleted` to imitate the delete process.)

There are two reasons for it. First, our files are really small -- we speak of kilobytes here, and being put on a compressed filesystem, like I did in this case, they are highly unlikely to ever exhaust the disk space on any modern SD card, not mentioning real hard disks.

Second, I did not want a glitch in a board implementation or lets say a bug in my backup server implementation to accidentally delete all my kittens and kill the board backups -- or the other way around.

PS. Even if one would ever need a delete, a simple cron job server-side would do in most cases, and in some rare ones one would just have to make sure that there are at least a few most recent undelted verions left; see also the bit about "most recent version" below.

### 10-minute intervals


### push and pull

The existing API was extended to handle two independent board operations: "push to remote", which we call "stash", reusing one of git verbs, and "pull from remote", which we accordingly call "unstash".

The respected API endpoints are `/stash-board/<id>` and `/unstash-board`, and, to make a bit of a difference, this time ht epayload format is just `json` (`application/json`) both ways.



<!-- 10-minute intervals; versions -->
<!-- security considerations -->




<!------------------------------------------------------------>

[apankrat-nb]: https://github.com/apankrat/nullboard
[apankrat-nb-issue-54]: https://github.com/apankrat/nullboard/issues/54
[apankrat-nb-issue-57]: https://github.com/apankrat/nullboard/issues/57#issuecomment-1125926959
[ofryl-nodejs-bk]: https://github.com/OfryL/nullboard-nodejs-agent
[apankrat-nb-4jag]: https://github.com/apankrat/nullboard/issues/54#issuecomment-1139188206
[nb-poc-commit-f790731c96]: https://github.com/gf-mse/nullboard/commit/f790731c96d77b2183d2a3973ecd8b1ca866c321
[nullboard-poc-dev]: https://github.com/gf-mse/nullboard/tree/dev/
[flask-cors]: https://flask-cors.readthedocs.io/en/3.0.10/
[nullboard-agent]: https://github.com/apankrat/nullboard-agent
[cors-protocol-spec]: https://fetch.spec.whatwg.org/#http-cors-protocol
[on-flask-data-fields]: https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request
[flask-is-json-2.2.x]: https://flask.palletsprojects.com/en/2.2.x/api/#flask.Request.is_json
[flask-form-field]: https://flask.palletsprojects.com/en/2.2.x/api/#flask.Request.form
[flask-json-field]: https://flask.palletsprojects.com/en/2.2.x/api/#flask.Request.json
