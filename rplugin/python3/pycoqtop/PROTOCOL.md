Protocol documentation
======================

CoqTop proposes an XML protocol to send commands and receive results.  We use
that protocol, but it is not clearly defined anywhare.  Some documentation can
be found here: https://github.com/siegebell/vscoq/wiki, but it is targeted
at a specific version of the protocol, so it doesn't work with more recent
versions of coq.  Another source of knowledge about the protocol is its
implementation in coqide, whose latest version can be found at
https://github.com/coq/coq/blob/master/ide/interface.mli.

If you want to test something, you can run the following command to start coqtop
in the same mode as in coquille:

```bash
coqtop -ideslave -main-channel stdfds -async-proofs -R . '' -async-proofs-tactic-error-resilience off
```

Data types
----------

* _Unit_: `<unit />`
* _Bool_: `<bool val="true">True</bool>` or `<bool val="false">False</bool>`
* _String_: `<string>my text</string>`
* _Int_: `<int>42</int>`
* _StateId_: `<state_id val="5" />`
* _RouteId_: `<route_id val="3" />`
* _List_: `<list>...</list>`
* _Option_: `<option val="none">` or `<option val="some">...</option>`
* _Pair_: `<pair>...<pair>`
* _Inl_: `<union val="in_l">...</union>`
* _Inr_: `<union val="in_r">...</union>`
* And many more...

Commands
--------

A command is represented as a `call` object. This object has a type and a value.
The type is set in the `val` attribute, while the value is the first child of
the call object.

Here is a list of call types and their associated value type.

### Init

This command is used to initialize coqtop. It must be the first command sent
to coqtop, otherwise coqtop will not process anything. It doesn't have arguments,
so its value must be None:

```xml
<call val="Init"><option val="none" /></call>
```

### Query

The query command is used to send queries to coqtop that are not present in
the file, such as `Print`, `Search`, etc.  The value type is a pair of a route\_id
and another pair of a string (containing the request) and a state\_id. Examples:

```xml
<call val="Query"><pair><route_id val="0" /><pair><string>Print nat.</string><state_id val="1" /></pair></pair></call>
<call val="Query"><pair><route_id val="0" /><pair><string>SearchAbout nat.</string><state_id val="1" /></pair></pair></call>
<call val="Query"><pair><route_id val="0" /><pair><string>Search (_ = S _).</string><state_id val="1" /></pair></pair></call>
```
