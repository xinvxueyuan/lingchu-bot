# Lingchu Bot Domain Language

Lingchu Bot connects messaging platforms to project-owned automation while
keeping external actors, platform identities, and business capabilities
separate.

## External Control Plane

**Service Principal**:
An external application identity authenticated independently from messaging
platform users.
_Avoid_: MCP user, bot user, virtual QQ user

**Capability Scope**:
A named class of operations a Service Principal may request, such as reading or
sending messages. It does not identify which messaging resources are allowed.
_Avoid_: permission level, resource permission

**Resource Grant**:
An explicit authorization connecting a Service Principal to a platform,
adapter, bot, conversation type, and conversation. A Capability Scope and a
matching Resource Grant are both required for access.
_Avoid_: token scope, wildcard permission

**External Operation**:
An attributable request from a Service Principal to read data or execute one
project-owned business capability.
_Avoid_: API passthrough, arbitrary bot call

## Messaging

**Message Envelope**:
The platform-neutral, privacy-bounded representation of a stored message made
available to external clients.
_Avoid_: raw event, adapter payload

**Message Segment**:
An ordered text or image element within an outbound message. A message is
accepted only when its target platform can preserve the complete segment order.
_Avoid_: attachment list, text plus images

**Message Cursor**:
An opaque continuation token bound to one Service Principal, Resource Grant,
and query. It carries no transferable authority.
_Avoid_: page number, database offset

**Bot Address**:
The complete platform, adapter, protocol, and bot identity used to select one
connected bot deterministically.
_Avoid_: first bot, current bot
