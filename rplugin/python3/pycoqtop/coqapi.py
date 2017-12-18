import xml.etree.ElementTree as ET
from pycoqtop.xmltype import *

def build(tag, val=None, children=[]):
    attribs = {'val': val} if val is not None else {}
    xml = ET.Element(tag, attribs)
    xml.extend(children)
    return xml

def encode_value(v):
    if v == ():
        return build('unit')
    elif isinstance(v, bool):
        xml = build('bool', str(v).lower())
        xml.text = str(v)
        return xml
    elif isinstance(v, str):# or isinstance(v, unicode):
        xml = build('string')
        xml.text = v
        return xml
    elif isinstance(v, int):
        xml = build('int')
        xml.text = str(v)
        return xml
    elif isinstance(v, StateId):
        return build('state_id', str(v.id))
    elif isinstance(v, list):
        return build('list', None, [encode_value(c) for c in v])
    elif isinstance(v, Option):
        xml = build('option')
        if v.val is not None:
            xml.set('val', 'some')
            xml.append(encode_value(v.val))
        else:
            xml.set('val', 'none')
        return xml
    elif isinstance(v, Inl):
        return build('union', 'in_l', [encode_value(v.val)])
    elif isinstance(v, Inr):
        return build('union', 'in_r', [encode_value(v.val)])
    # NB: `tuple` check must be at the end because it overlaps with () and
    # namedtuples.
    elif isinstance(v, tuple):
        return build('pair', None, [encode_value(c) for c in v])
    else:
        assert False, 'unrecognized type in encode_value: %r' % (type(v),)

def parse_value(xml):
    if xml.tag == 'unit':
        return ()
    elif xml.tag == 'bool':
        if xml.get('val') == 'true':
            return True
        elif xml.get('val') == 'false':
            return False
        else:
            assert False, 'expected "true" or "false" in <bool>'
    elif xml.tag == 'string':
        return xml.text or ''
    elif xml.tag == 'int':
        return int(xml.text)
    elif xml.tag == 'state_id':
        return StateId(int(xml.get('val')))
    elif xml.tag == 'list':
        return [parse_value(c) for c in xml]
    elif xml.tag == 'option':
        if xml.get('val') == 'none':
            return Option(None)
        elif xml.get('val') == 'some':
            return Option(parse_value(xml[0]))
        else:
            assert False, 'expected "none" or "some" in <option>'
    elif xml.tag == 'pair':
        return tuple(parse_value(c) for c in xml)
    elif xml.tag == 'union':
        if xml.get('val') == 'in_l':
            return Inl(parse_value(xml[0]))
        elif xml.get('val') == 'in_r':
            return Inr(parse_value(xml[0]))
        else:
            assert False, 'expected "in_l" or "in_r" in <union>'
    elif xml.tag == 'option_state':
        sync, depr, name, value = map(parse_value, xml)
        return OptionState(sync, depr, name, value)
    elif xml.tag == 'option_value':
        return OptionValue(parse_value(xml[0]))
    elif xml.tag == 'status':
        path, proofname, allproofs, proofnum = map(parse_value, xml)
        return Status(path, proofname, allproofs, proofnum)
    elif xml.tag == 'goals':
        return Goals(*map(parse_value, xml))
    elif xml.tag == 'goal':
        return Goal(*map(parse_value, xml))
    elif xml.tag == 'evar':
        return Evar(*map(parse_value, xml))
    elif xml.tag == 'xml' or xml.tag == 'richpp':
        parts = []
        child = 0
        try:
            c = xml.getchildren()[child]
        except:
            c = None
        for p in xml.itertext():
            if c is None:
                parts.append(p)
                continue
            if c.text == p:
                parts.append(parse_value(c))
                child = child + 1
                try:
                    c = xml.getchildren()[child]
                except:
                    c = None
            parts.append(p)
        return RichPP(parts)
    elif xml.tag == 'message':
        for c in xml.getchildren():
            if c.tag == 'richpp':
                return [parse_value(c)]

class Ok:
    def __init__(self, value, messages):
        self.val = value
        self.msg = [parse_value(c) for c in messages]
        pass

class Err:
    def __init__(self, error, messages):
        self.err = error
        self.msg = [parse_value(c) for c in messages]
        pass

class API:
    def __init__(self):
        pass

    def encode_call(self, name, arg):
        return build('call', name, [encode_value(arg)])
    
    def get_init_msg(self, encoding = 'utf-8'):
        xml = self.encode_call('Init', Option(None))
        return ET.tostring(xml, encoding)

    def get_call_msg(self, name, arg, encoding = 'utf-8'):
        xml = self.encode_call(name, arg)
        return ET.tostring(xml, encoding)

    def response_end(self, xml):
        for c in xml.getchildren():
            if c.tag == 'value':
                return False
        return True

    def parse_response(self, xml):
        messageNodes = []
        valueNodes = []
        for c in xml.getchildren():
            if c.tag == 'value':
                valueNodes.append(c)
            if c.tag == 'message':
                messageNodes.append(c)
        if len(valueNodes) > 1:
            for c in valueNodes:
                for d in list(parse_value(c[0])):
                    if isinstance(d, StateId):
                        valueNode = c
        elif len(valueNodes) == 1:
            valueNode = valueNodes[0]
        else:
            valueNode = None
        if valueNode.get('val') == 'good':
            return Ok(parse_value(valueNode[0]), messageNodes)
        if valueNode.get('val') == 'fail':
            return Err(parse_value(valueNode[1]), messageNodes)
        assert False, "Unexpected answer from coqtop: " + ET.tostring(xml)
