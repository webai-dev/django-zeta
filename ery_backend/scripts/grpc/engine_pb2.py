# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: engine.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='engine.proto',
  package='main',
  syntax='proto3',
  serialized_options=_b('Z\006protos'),
  serialized_pb=_b('\n\x0c\x65ngine.proto\x12\x04main\"9\n\nJavascript\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0f\n\x07version\x18\x02 \x01(\t\x12\x0c\n\x04\x63ode\x18\x03 \x01(\t\"n\n\x06Struct\x12(\n\x06\x66ields\x18\x01 \x03(\x0b\x32\x18.main.Struct.FieldsEntry\x1a:\n\x0b\x46ieldsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1a\n\x05value\x18\x02 \x01(\x0b\x32\x0b.main.Value:\x02\x38\x01\"(\n\tListValue\x12\x1b\n\x06values\x18\x01 \x03(\x0b\x32\x0b.main.Value\"\xa2\x01\n\x05Value\x12\x14\n\nbool_value\x18\x01 \x01(\x08H\x00\x12\x16\n\x0cnumber_value\x18\x02 \x01(\x01H\x00\x12\x16\n\x0cstring_value\x18\x03 \x01(\tH\x00\x12%\n\nlist_value\x18\x04 \x01(\x0b\x32\x0f.main.ListValueH\x00\x12$\n\x0cstruct_value\x18\x05 \x01(\x0b\x32\x0c.main.StructH\x00\x42\x06\n\x04kind\"F\n\x08Variable\x12\x1e\n\x16variable_definition_id\x18\x01 \x01(\x03\x12\x1a\n\x05value\x18\x02 \x01(\x0b\x32\x0b.main.Value\"\x14\n\x04Hand\x12\x0c\n\x04name\x18\x01 \x01(\t\"z\n\x04Team\x12\x0c\n\x04name\x18\x01 \x01(\t\x12(\n\x07members\x18\x02 \x03(\x0b\x32\x17.main.Team.MembersEntry\x1a:\n\x0cMembersEntry\x12\x0b\n\x03key\x18\x01 \x01(\x05\x12\x19\n\x05value\x18\x02 \x01(\x0b\x32\n.main.Hand:\x02\x38\x01\"v\n\x05Stint\x12\x0c\n\x04name\x18\x01 \x01(\t\x12%\n\x05teams\x18\x02 \x03(\x0b\x32\x16.main.Stint.TeamsEntry\x1a\x38\n\nTeamsEntry\x12\x0b\n\x03key\x18\x01 \x01(\x05\x12\x19\n\x05value\x18\x02 \x01(\x0b\x32\n.main.Team:\x02\x38\x01\"\x13\n\x03\x45ra\x12\x0c\n\x04name\x18\x01 \x01(\t\"\x15\n\x05Stage\x12\x0c\n\x04name\x18\x01 \x01(\t\"\xcc\x01\n\x07\x43ontext\x12/\n\tvariables\x18\x01 \x03(\x0b\x32\x1c.main.Context.VariablesEntry\x12\x1a\n\x05stint\x18\x02 \x01(\x0b\x32\x0b.main.Stint\x12\x16\n\x03\x65ra\x18\x03 \x01(\x0b\x32\t.main.Era\x12\x1a\n\x05stage\x18\x04 \x01(\x0b\x32\x0b.main.Stage\x1a@\n\x0eVariablesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1d\n\x05value\x18\x02 \x01(\x0b\x32\x0e.main.Variable:\x02\x38\x01\"\x90\x01\n\x05State\x12-\n\tvariables\x18\x01 \x03(\x0b\x32\x1a.main.State.VariablesEntry\x12\x16\n\x03\x65ra\x18\x02 \x01(\x0b\x32\t.main.Era\x1a@\n\x0eVariablesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1d\n\x05value\x18\x02 \x01(\x0b\x32\x0e.main.Variable:\x02\x38\x01\"P\n\x0cJavascriptOp\x12 \n\x06script\x18\x01 \x01(\x0b\x32\x10.main.Javascript\x12\x1e\n\x07\x63ontext\x18\x02 \x01(\x0b\x32\r.main.Context\"X\n\x06Result\x12\x1a\n\x05value\x18\x01 \x01(\x0b\x32\x0b.main.Value\x12\x1a\n\x05state\x18\x02 \x01(\x0b\x32\x0b.main.State\x12\x16\n\x0e\x65xecution_time\x18\x03 \x01(\x01*6\n\tScopeEnum\x12\x08\n\x04HAND\x10\x00\x12\x08\n\x04TEAM\x10\x01\x12\n\n\x06MODULE\x10\x02\x12\t\n\x05STINT\x10\x03\x32=\n\x10JavascriptEngine\x12)\n\x03Run\x12\x12.main.JavascriptOp\x1a\x0c.main.Result\"\x00\x42\x08Z\x06protosb\x06proto3')
)

_SCOPEENUM = _descriptor.EnumDescriptor(
  name='ScopeEnum',
  full_name='main.ScopeEnum',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='HAND', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TEAM', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MODULE', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='STINT', index=3, number=3,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=1308,
  serialized_end=1362,
)
_sym_db.RegisterEnumDescriptor(_SCOPEENUM)

ScopeEnum = enum_type_wrapper.EnumTypeWrapper(_SCOPEENUM)
HAND = 0
TEAM = 1
MODULE = 2
STINT = 3



_JAVASCRIPT = _descriptor.Descriptor(
  name='Javascript',
  full_name='main.Javascript',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='main.Javascript.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='version', full_name='main.Javascript.version', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='code', full_name='main.Javascript.code', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=22,
  serialized_end=79,
)


_STRUCT_FIELDSENTRY = _descriptor.Descriptor(
  name='FieldsEntry',
  full_name='main.Struct.FieldsEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='main.Struct.FieldsEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='main.Struct.FieldsEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=_b('8\001'),
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=133,
  serialized_end=191,
)

_STRUCT = _descriptor.Descriptor(
  name='Struct',
  full_name='main.Struct',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='fields', full_name='main.Struct.fields', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_STRUCT_FIELDSENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=81,
  serialized_end=191,
)


_LISTVALUE = _descriptor.Descriptor(
  name='ListValue',
  full_name='main.ListValue',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='values', full_name='main.ListValue.values', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=193,
  serialized_end=233,
)


_VALUE = _descriptor.Descriptor(
  name='Value',
  full_name='main.Value',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='bool_value', full_name='main.Value.bool_value', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='number_value', full_name='main.Value.number_value', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='string_value', full_name='main.Value.string_value', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='list_value', full_name='main.Value.list_value', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='struct_value', full_name='main.Value.struct_value', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='kind', full_name='main.Value.kind',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=236,
  serialized_end=398,
)


_VARIABLE = _descriptor.Descriptor(
  name='Variable',
  full_name='main.Variable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='variable_definition_id', full_name='main.Variable.variable_definition_id', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='main.Variable.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=400,
  serialized_end=470,
)


_HAND = _descriptor.Descriptor(
  name='Hand',
  full_name='main.Hand',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='main.Hand.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=472,
  serialized_end=492,
)


_TEAM_MEMBERSENTRY = _descriptor.Descriptor(
  name='MembersEntry',
  full_name='main.Team.MembersEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='main.Team.MembersEntry.key', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='main.Team.MembersEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=_b('8\001'),
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=558,
  serialized_end=616,
)

_TEAM = _descriptor.Descriptor(
  name='Team',
  full_name='main.Team',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='main.Team.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='members', full_name='main.Team.members', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_TEAM_MEMBERSENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=494,
  serialized_end=616,
)


_STINT_TEAMSENTRY = _descriptor.Descriptor(
  name='TeamsEntry',
  full_name='main.Stint.TeamsEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='main.Stint.TeamsEntry.key', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='main.Stint.TeamsEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=_b('8\001'),
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=680,
  serialized_end=736,
)

_STINT = _descriptor.Descriptor(
  name='Stint',
  full_name='main.Stint',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='main.Stint.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='teams', full_name='main.Stint.teams', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_STINT_TEAMSENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=618,
  serialized_end=736,
)


_ERA = _descriptor.Descriptor(
  name='Era',
  full_name='main.Era',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='main.Era.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=738,
  serialized_end=757,
)


_STAGE = _descriptor.Descriptor(
  name='Stage',
  full_name='main.Stage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='main.Stage.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=759,
  serialized_end=780,
)


_CONTEXT_VARIABLESENTRY = _descriptor.Descriptor(
  name='VariablesEntry',
  full_name='main.Context.VariablesEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='main.Context.VariablesEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='main.Context.VariablesEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=_b('8\001'),
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=923,
  serialized_end=987,
)

_CONTEXT = _descriptor.Descriptor(
  name='Context',
  full_name='main.Context',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='variables', full_name='main.Context.variables', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='stint', full_name='main.Context.stint', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='era', full_name='main.Context.era', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='stage', full_name='main.Context.stage', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_CONTEXT_VARIABLESENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=783,
  serialized_end=987,
)


_STATE_VARIABLESENTRY = _descriptor.Descriptor(
  name='VariablesEntry',
  full_name='main.State.VariablesEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='main.State.VariablesEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='value', full_name='main.State.VariablesEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=_b('8\001'),
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=923,
  serialized_end=987,
)

_STATE = _descriptor.Descriptor(
  name='State',
  full_name='main.State',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='variables', full_name='main.State.variables', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='era', full_name='main.State.era', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_STATE_VARIABLESENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=990,
  serialized_end=1134,
)


_JAVASCRIPTOP = _descriptor.Descriptor(
  name='JavascriptOp',
  full_name='main.JavascriptOp',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='script', full_name='main.JavascriptOp.script', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='context', full_name='main.JavascriptOp.context', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1136,
  serialized_end=1216,
)


_RESULT = _descriptor.Descriptor(
  name='Result',
  full_name='main.Result',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='main.Result.value', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='state', full_name='main.Result.state', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='execution_time', full_name='main.Result.execution_time', index=2,
      number=3, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1218,
  serialized_end=1306,
)

_STRUCT_FIELDSENTRY.fields_by_name['value'].message_type = _VALUE
_STRUCT_FIELDSENTRY.containing_type = _STRUCT
_STRUCT.fields_by_name['fields'].message_type = _STRUCT_FIELDSENTRY
_LISTVALUE.fields_by_name['values'].message_type = _VALUE
_VALUE.fields_by_name['list_value'].message_type = _LISTVALUE
_VALUE.fields_by_name['struct_value'].message_type = _STRUCT
_VALUE.oneofs_by_name['kind'].fields.append(
  _VALUE.fields_by_name['bool_value'])
_VALUE.fields_by_name['bool_value'].containing_oneof = _VALUE.oneofs_by_name['kind']
_VALUE.oneofs_by_name['kind'].fields.append(
  _VALUE.fields_by_name['number_value'])
_VALUE.fields_by_name['number_value'].containing_oneof = _VALUE.oneofs_by_name['kind']
_VALUE.oneofs_by_name['kind'].fields.append(
  _VALUE.fields_by_name['string_value'])
_VALUE.fields_by_name['string_value'].containing_oneof = _VALUE.oneofs_by_name['kind']
_VALUE.oneofs_by_name['kind'].fields.append(
  _VALUE.fields_by_name['list_value'])
_VALUE.fields_by_name['list_value'].containing_oneof = _VALUE.oneofs_by_name['kind']
_VALUE.oneofs_by_name['kind'].fields.append(
  _VALUE.fields_by_name['struct_value'])
_VALUE.fields_by_name['struct_value'].containing_oneof = _VALUE.oneofs_by_name['kind']
_VARIABLE.fields_by_name['value'].message_type = _VALUE
_TEAM_MEMBERSENTRY.fields_by_name['value'].message_type = _HAND
_TEAM_MEMBERSENTRY.containing_type = _TEAM
_TEAM.fields_by_name['members'].message_type = _TEAM_MEMBERSENTRY
_STINT_TEAMSENTRY.fields_by_name['value'].message_type = _TEAM
_STINT_TEAMSENTRY.containing_type = _STINT
_STINT.fields_by_name['teams'].message_type = _STINT_TEAMSENTRY
_CONTEXT_VARIABLESENTRY.fields_by_name['value'].message_type = _VARIABLE
_CONTEXT_VARIABLESENTRY.containing_type = _CONTEXT
_CONTEXT.fields_by_name['variables'].message_type = _CONTEXT_VARIABLESENTRY
_CONTEXT.fields_by_name['stint'].message_type = _STINT
_CONTEXT.fields_by_name['era'].message_type = _ERA
_CONTEXT.fields_by_name['stage'].message_type = _STAGE
_STATE_VARIABLESENTRY.fields_by_name['value'].message_type = _VARIABLE
_STATE_VARIABLESENTRY.containing_type = _STATE
_STATE.fields_by_name['variables'].message_type = _STATE_VARIABLESENTRY
_STATE.fields_by_name['era'].message_type = _ERA
_JAVASCRIPTOP.fields_by_name['script'].message_type = _JAVASCRIPT
_JAVASCRIPTOP.fields_by_name['context'].message_type = _CONTEXT
_RESULT.fields_by_name['value'].message_type = _VALUE
_RESULT.fields_by_name['state'].message_type = _STATE
DESCRIPTOR.message_types_by_name['Javascript'] = _JAVASCRIPT
DESCRIPTOR.message_types_by_name['Struct'] = _STRUCT
DESCRIPTOR.message_types_by_name['ListValue'] = _LISTVALUE
DESCRIPTOR.message_types_by_name['Value'] = _VALUE
DESCRIPTOR.message_types_by_name['Variable'] = _VARIABLE
DESCRIPTOR.message_types_by_name['Hand'] = _HAND
DESCRIPTOR.message_types_by_name['Team'] = _TEAM
DESCRIPTOR.message_types_by_name['Stint'] = _STINT
DESCRIPTOR.message_types_by_name['Era'] = _ERA
DESCRIPTOR.message_types_by_name['Stage'] = _STAGE
DESCRIPTOR.message_types_by_name['Context'] = _CONTEXT
DESCRIPTOR.message_types_by_name['State'] = _STATE
DESCRIPTOR.message_types_by_name['JavascriptOp'] = _JAVASCRIPTOP
DESCRIPTOR.message_types_by_name['Result'] = _RESULT
DESCRIPTOR.enum_types_by_name['ScopeEnum'] = _SCOPEENUM
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Javascript = _reflection.GeneratedProtocolMessageType('Javascript', (_message.Message,), dict(
  DESCRIPTOR = _JAVASCRIPT,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Javascript)
  ))
_sym_db.RegisterMessage(Javascript)

Struct = _reflection.GeneratedProtocolMessageType('Struct', (_message.Message,), dict(

  FieldsEntry = _reflection.GeneratedProtocolMessageType('FieldsEntry', (_message.Message,), dict(
    DESCRIPTOR = _STRUCT_FIELDSENTRY,
    __module__ = 'engine_pb2'
    # @@protoc_insertion_point(class_scope:main.Struct.FieldsEntry)
    ))
  ,
  DESCRIPTOR = _STRUCT,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Struct)
  ))
_sym_db.RegisterMessage(Struct)
_sym_db.RegisterMessage(Struct.FieldsEntry)

ListValue = _reflection.GeneratedProtocolMessageType('ListValue', (_message.Message,), dict(
  DESCRIPTOR = _LISTVALUE,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.ListValue)
  ))
_sym_db.RegisterMessage(ListValue)

Value = _reflection.GeneratedProtocolMessageType('Value', (_message.Message,), dict(
  DESCRIPTOR = _VALUE,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Value)
  ))
_sym_db.RegisterMessage(Value)

Variable = _reflection.GeneratedProtocolMessageType('Variable', (_message.Message,), dict(
  DESCRIPTOR = _VARIABLE,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Variable)
  ))
_sym_db.RegisterMessage(Variable)

Hand = _reflection.GeneratedProtocolMessageType('Hand', (_message.Message,), dict(
  DESCRIPTOR = _HAND,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Hand)
  ))
_sym_db.RegisterMessage(Hand)

Team = _reflection.GeneratedProtocolMessageType('Team', (_message.Message,), dict(

  MembersEntry = _reflection.GeneratedProtocolMessageType('MembersEntry', (_message.Message,), dict(
    DESCRIPTOR = _TEAM_MEMBERSENTRY,
    __module__ = 'engine_pb2'
    # @@protoc_insertion_point(class_scope:main.Team.MembersEntry)
    ))
  ,
  DESCRIPTOR = _TEAM,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Team)
  ))
_sym_db.RegisterMessage(Team)
_sym_db.RegisterMessage(Team.MembersEntry)

Stint = _reflection.GeneratedProtocolMessageType('Stint', (_message.Message,), dict(

  TeamsEntry = _reflection.GeneratedProtocolMessageType('TeamsEntry', (_message.Message,), dict(
    DESCRIPTOR = _STINT_TEAMSENTRY,
    __module__ = 'engine_pb2'
    # @@protoc_insertion_point(class_scope:main.Stint.TeamsEntry)
    ))
  ,
  DESCRIPTOR = _STINT,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Stint)
  ))
_sym_db.RegisterMessage(Stint)
_sym_db.RegisterMessage(Stint.TeamsEntry)

Era = _reflection.GeneratedProtocolMessageType('Era', (_message.Message,), dict(
  DESCRIPTOR = _ERA,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Era)
  ))
_sym_db.RegisterMessage(Era)

Stage = _reflection.GeneratedProtocolMessageType('Stage', (_message.Message,), dict(
  DESCRIPTOR = _STAGE,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Stage)
  ))
_sym_db.RegisterMessage(Stage)

Context = _reflection.GeneratedProtocolMessageType('Context', (_message.Message,), dict(

  VariablesEntry = _reflection.GeneratedProtocolMessageType('VariablesEntry', (_message.Message,), dict(
    DESCRIPTOR = _CONTEXT_VARIABLESENTRY,
    __module__ = 'engine_pb2'
    # @@protoc_insertion_point(class_scope:main.Context.VariablesEntry)
    ))
  ,
  DESCRIPTOR = _CONTEXT,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Context)
  ))
_sym_db.RegisterMessage(Context)
_sym_db.RegisterMessage(Context.VariablesEntry)

State = _reflection.GeneratedProtocolMessageType('State', (_message.Message,), dict(

  VariablesEntry = _reflection.GeneratedProtocolMessageType('VariablesEntry', (_message.Message,), dict(
    DESCRIPTOR = _STATE_VARIABLESENTRY,
    __module__ = 'engine_pb2'
    # @@protoc_insertion_point(class_scope:main.State.VariablesEntry)
    ))
  ,
  DESCRIPTOR = _STATE,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.State)
  ))
_sym_db.RegisterMessage(State)
_sym_db.RegisterMessage(State.VariablesEntry)

JavascriptOp = _reflection.GeneratedProtocolMessageType('JavascriptOp', (_message.Message,), dict(
  DESCRIPTOR = _JAVASCRIPTOP,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.JavascriptOp)
  ))
_sym_db.RegisterMessage(JavascriptOp)

Result = _reflection.GeneratedProtocolMessageType('Result', (_message.Message,), dict(
  DESCRIPTOR = _RESULT,
  __module__ = 'engine_pb2'
  # @@protoc_insertion_point(class_scope:main.Result)
  ))
_sym_db.RegisterMessage(Result)


DESCRIPTOR._options = None
_STRUCT_FIELDSENTRY._options = None
_TEAM_MEMBERSENTRY._options = None
_STINT_TEAMSENTRY._options = None
_CONTEXT_VARIABLESENTRY._options = None
_STATE_VARIABLESENTRY._options = None

_JAVASCRIPTENGINE = _descriptor.ServiceDescriptor(
  name='JavascriptEngine',
  full_name='main.JavascriptEngine',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=1364,
  serialized_end=1425,
  methods=[
  _descriptor.MethodDescriptor(
    name='Run',
    full_name='main.JavascriptEngine.Run',
    index=0,
    containing_service=None,
    input_type=_JAVASCRIPTOP,
    output_type=_RESULT,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_JAVASCRIPTENGINE)

DESCRIPTOR.services_by_name['JavascriptEngine'] = _JAVASCRIPTENGINE

# @@protoc_insertion_point(module_scope)
