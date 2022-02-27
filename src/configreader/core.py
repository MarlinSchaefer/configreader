import ast
import numpy as np
from collections import OrderedDict
from configparser import ConfigParser


class ExpressionString(object):
    def __init__(self):
        self.functions = {'sin': np.sin,
                          'cos': np.cos,
                          'tan': np.tan,
                          'exp': np.exp,
                          'root': np.sqrt,
                          'sqrt': np.sqrt,
                          'sum': sum,
                          'int': int,
                          'float': float,
                          'bool': bool,
                          'str': str}
        self.constants = {'pi': np.pi,
                          'Pi': np.pi,
                          'PI': np.pi,
                          'e': np.e,
                          'E': np.e}

    def register_function(self, func, name=None):
        if callable(func):
            if name is None:
                name = func.__name__
            self.functions[name] = func

    def register_constant(self, name, val):
        self.constants[name] = val

    def parse_Call(self, node):
        funcname = node.func.id
        if funcname not in self.functions:
            raise ValueError(f'Unknown function {funcname}')
        args = [self.parse_node(arg) for arg in node.args]
        kwargs = {kwarg.arg: self.parse_node(kwarg.value)
                  for kwarg in node.keywords}
        return self.functions[funcname](*args, **kwargs)

    def parse_Constant(self, node):
        val = node.value
        if isinstance(val, str) and val in self.constants:
            val = self.constants[val]
        return val

    def parse_Name(self, node):
        val = node.id
        if val in self.constants:
            val = self.constants[val]
        return val

    def parse_BinOp(self, node):
        ops = {'add': lambda x, y: x + y,
               'sub': lambda x, y: x - y,
               'mul': lambda x, y: x * y,
               'div': lambda x, y: x / y,
               'fdiv': lambda x, y: x // y,
               'mod': lambda x, y: x % y,
               'pow': lambda x, y: x ** y}
        if isinstance(node.op, ast.Add):
            op = 'add'
        elif isinstance(node.op, ast.Sub):
            op = 'sub'
        elif isinstance(node.op, ast.Mult):
            op = 'mul'
        elif isinstance(node.op, ast.Div):
            op = 'div'
        elif isinstance(node.op, ast.FloorDiv):
            op = 'fdiv'
        elif isinstance(node.op, ast.Mod):
            op = 'mod'
        else:
            raise ValueError(f'Unhandled binary operator {node.op}')
        return ops[op](self.parse_node(node.left),
                       self.parse_node(node.right))

    def parse_UnaryOp(self, node):
        ops = {'plus': lambda x: +x,
               'minus': lambda x: -x,
               'not': lambda x: not x,
               'inv': lambda x: ~x}
        if isinstance(node.op, ast.UAdd):
            op = 'plus'
        elif isinstance(node.op, ast.USub):
            op = 'minus'
        elif isinstance(node.op, ast.Not):
            op = 'not'
        elif isinstance(node.op, ast.Invert):
            op = 'inv'
        else:
            raise ValueError(f'Unrecognized unary operator {op}')
        return ops[op](self.parse_node(node.operand))

    def parse_BoolOp(self, node):
        ops = {'and': all,
               'or': any}
        if isinstance(node.op, ast.And):
            op = 'and'
        elif isinstance(node.op, ast.Or):
            op = 'or'
        else:
            raise ValueError(f'Unhandled boolean operator {node.op}')
        if len(node.values) < 2:
            raise ValueError('Insufficient number of arguments for boolean '
                             'operation.')
        return ops[op]([self.parse_node(n) for n in node.values])

    def parse_Compare(self, node):
        ops = {'eq': lambda x, y: x == y,
               'neq': lambda x, y: x != y,
               'lt': lambda x, y: x < y,
               'lte': lambda x, y: x <= y,
               'gt': lambda x, y: x > y,
               'gte': lambda x, y: x >= y,
               'is': lambda x, y: x is y,
               'nis': lambda x, y: x is not y,
               'in': lambda x, y: x in y,
               'nin': lambda x, y: x not in y}
        left = self.parse_node(node.left)
        res = []
        for op, val in zip(node.ops, node.comparators):
            val = self.parse_node(val)
            if isinstance(op, ast.Eq):
                op = 'eq'
            elif isinstance(op, ast.NotEq):
                op = 'neq'
            elif isinstance(op, ast.Lt):
                op = 'lt'
            elif isinstance(op, ast.LtE):
                op = 'lte'
            elif isinstance(op, ast.Gt):
                op = 'gt'
            elif isinstance(op, ast.GtE):
                op = 'gte'
            elif isinstance(op, ast.Is):
                op = 'is'
            elif isinstance(op, ast.IsNot):
                op = 'nis'
            elif isinstance(op, ast.In):
                op = 'in'
            elif isinstance(op, ast.NotIn):
                op = 'nin'
            else:
                raise ValueError(f'Unrecognized comparison {op}')
            res.append(ops[op](left, val))
            left = val
        return all(res)

    def parse_List(self, node):
        return [self.parse_node(n) for n in node.elts]

    def parse_Tuple(self, node):
        return (self.parse_node(n) for n in node.elts)

    def parse_Set(self, node):
        return {self.parse_node(n) for n in node.elts}

    def parse_Dict(self, node):
        keys = [self.parse_node(n) for n in node.keys]
        vals = [self.parse_node(n) for n in node.values]
        return {k: v for (k, v) in zip(keys, vals)}

    def parse_Expression(self, node):
        return self.parse_node(node.body)

    def parse_Module(self, node):
        values = node.body
        if len(values) == 1:
            return self.parse_node(values[0])
        else:
            return [self.parse_node(n) for n in values]

    def parse_Expr(self, node):
        return self.parse_node(node.value)

    def parse_node(self, node):
        cls_name = node.__class__.__name__
        parse_name = f'parse_{cls_name}'
        if hasattr(self, parse_name):
            parse_func = getattr(self, parse_name)
        else:
            raise ValueError(f'Forbidden node: {cls_name}')
        return parse_func(node)

    def parse(self, string):
        tree = ast.parse(string)
        return self.parse_node(tree)
    pass


class SmartGet(object):
    values = {'all': 2,
              'section': 1,
              'content': 0}

    def __init__(self, value):
        if isinstance(value, self.__class__):
            value = value.value
        if isinstance(value, str):
            self.value = self.values[value.lower()]
        elif value in self.values.values():
            self.value = value

    def includes(self, other):
        if isinstance(other, self.__class__):
            other = other.value
        elif isinstance(other, str):
            if other not in self.values:
                raise ValueError(f'Unrecognized SmartGet {other}')
            other = self.values[other]
        return self.value >= other


class Missing(object):
    def __str__(self):
        return "Missing"

    def __repr__(self):
        Missing()


class MissingKeyError(KeyError):
    pass


class NonUniqueKeyError(KeyError):
    pass


class MissingSubsectionError(KeyError):
    pass


class Section(object):
    def __init__(self, name, parent=None, sep='/', content=None,
                 smart_get=None, smart_get_unique=True):
        self.name = name
        self.sep = sep
        self.content = content if content is not None else {}
        self.parent = parent
        self.subsections = OrderedDict()
        self.smart_get = SmartGet('all')
        self.smart_get_unique = smart_get_unique

    @property
    def full_path(self):
        if self.parent is None:
            return self.name
        else:
            return f'{self.parent.full_path}{self.sep}{self.name}'

    def expand_sublevel(self, key):
        parts = key.split(self.sep)
        if len(parts) == 1:
            return self.full_path + self.sep + key
        if not key.startswith(self.sep) and parts[0] in self.subsections:
            parts.insert(0, "")
        full_path_parts = self.full_path.split(self.sep)
        for i, pt in enumerate(parts):
            if pt != "":
                break
            parts[i] = full_path_parts[i]
        return self.sep.join(parts)

    @property
    def toplevel(self):
        if self.parent is None:
            return self
        else:
            return self.parent.toplevel

    def split_exist(self, key):
        key = self.expand_sublevel(key)
        parts = key.split(self.sep)
        exists = []
        section = self.toplevel
        cname = parts.pop(0)
        if cname != section.full_path:
            raise RuntimeError('Could not identify toplevel')
        exists.append(cname)
        while len(parts) > 0:
            cname = parts.pop(0)
            if cname in section.subsections:
                section = section.subsections[cname]
                exists.append(cname)
            else:
                parts.insert(0, cname)
                break
        return exists, parts

    def is_direct_subsection(self, name):
        name = self.expand_sublevel(name)
        name = name.split(self.sep)[-1]
        if name in self.subsections:
            return True
        else:
            return False

    def find_subsections(self, name):
        ret = []
        for subsec in self.subsections.values():
            if name == subsec.name:
                ret.append(subsec.full_path)
            ret.extend(subsec.find_subsections(name))
        return ret

    def is_subsection(self, name):
        subsecs = self.find_subsections(name)
        return len(subsecs) > 0

    def get_from_path(self, path):
        section = self.toplevel
        parts = path.split(self.sep)
        topname = parts.pop(0)
        if section.name != topname:
            raise ValueError(f'Path {path} not found.')
        while len(parts) > 0:
            name = parts.pop(0)
            if name == "" and len(parts) == 0:
                return section
            if len(parts) == 0:
                if name in section.content:
                    return section.content[name]
                elif name in section.subsections:
                    return section.subsections[name]
                else:
                    raise MissingKeyError(f"Path {path} not found.")
            if name not in section.subsections:
                raise MissingKeyError(f"Path {path} not found.")
            section = section.subsections[name]

    def add_subsection(self, name, squeeze=True):
        exists, missing = self.split_exist(name)
        section = self.get_from_path(self.sep.join(exists + ['']))
        ret = []
        for mname in missing:
            tmp = Section(mname, parent=section, sep=self.sep,
                          smart_get=self.smart_get,
                          smart_get_unique=self.smart_get_unique)
            section.subsections[mname] = tmp
            section = tmp
            ret.append(tmp)
        if squeeze and len(ret) == 1:
            return ret[0]
        else:
            return ret

    def find_values(self, name, squeeze=True):
        ret = {}
        n = 0
        if name in self.content:
            ret[self.full_path] = self.content[name]
            n += 1
        for subsec in self.subsections.values():
            subdic, subn = subsec.find_values(name, squeeze=False)
            ret.update(subdic)
            n += subn
        if squeeze and len(ret) == 1:
            return ret[list(ret.keys())[0]], n
        else:
            return ret, n

    def find_value(self, name):
        values, n = self.find_values(name, squeeze=True)
        if n == 0:
            raise MissingKeyError(f'No value with key {name} found.')
        elif n > 1:
            raise NonUniqueKeyError(f'Found multiple values for key {name}: '
                                    f'{values}')
        return values

    def __setitem__(self, key, value):
        self.set(key, value)

    def set(self, key, value):
        path = self.expand_sublevel(key)
        path = path.split(self.sep)
        path.pop(0)
        valkey = path.pop(-1)
        section = self.toplevel
        for sname in path:
            if sname not in section.subsections:
                raise MissingSubsectionError()
            section = section.subsections[sname]
        section.content[valkey] = value

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key):
        if self.sep not in key:
            vals, n = self.find_values(key, squeeze=True)
            secs = self.find_subsections(key)
            secs = [self.get_from_path(sec) for sec in secs]
            total = n + len(secs)
            if total == 0:
                raise MissingKeyError(f'No value or section with key {key}.')
            if total > 1:
                raise NonUniqueKeyError('Found multiple values: '
                                        f'{list(vals.values())} and '
                                        'sections: '
                                        f'{[sec.full_path for sec in secs]}')
            if n == 0:
                return secs[0]
            else:
                return vals
        else:
            key = self.expand_sublevel(key)
            return self.get_from_path(key)

    def subsections(self):
        return list(self.subsections.keys())

    def sections(self):
        return self.subsections()


class SectionOld(object):
    def __init__(self, name, parent=None, sep='/', content=None,
                 smart_get=None, smart_get_unique=True):
        self.name = name
        self.sep = sep
        self.content = content if content is not None else {}
        self.parent = parent
        self.subsections = OrderedDict()
        self.smart_get = SmartGet('all')
        self.smart_get_unique = smart_get_unique

    @property
    def full_name(self):
        if self.parent is None:
            return self.name
        else:
            return self.sep.join([self.parent.full_name, self.name])

    def __contains__(self, key):
        return self.contains(key)

    def contains(self, key, smart_get=None):
        if smart_get is None:
            smart_get = self.smart_get

        if key in self.content:
            return True
        if smart_get.includes('section'):
            if key in self.subsections:
                return True
            for subsec in self.subsections.values():
                if key == subsec.name:
                    return True
                if key == subsec.full_name:
                    return True
            if smart_get.includes('all'):
                for subsec in self.subsections.values():
                    if key in subsec:
                        return True
        return False

    def has_subsection(self, name, recursive=True):
        if name.startswith(self.sep):
            name = self.full_name + name
        
        if name in self.subsections:
            return True
        for subsec in self.subsections.values():
            if subsec.full_name == name:
                return True
        if not recursive:
            return False
        ret = [subsec.has_subsection(name, recursive=True)
               for subsec in self.subsections.values()]
        return any(ret)

    def __getitem__(self, key):
        return self.get(key)

    def get_value(self, key):
        return self.content[key]

    def get_subsection(self, key):
        if key == self.name or key == self.full_name:
            raise ValueError('Key points to self')
        if key.startswith(self.sep):
            key = self.full_name + key
        if key in self.subsections:
            return self.subsections[key]
        for subsec in self.subsections.values():
            if subsec.full_name == key:
                return subsec
        raise KeyError(f'Subsection {key} not found')

    def get(self, key, smart_get=None, expand_subsection_key=True):
        if expand_subsection_key:
            if key.startswith(self.sep):
                key = self.full_name + key
            parts = key.split(self.sep)
            if len(parts) > 1:
                if self.sep.join(parts[:-1]) == self.full_name:
                    return self.content[parts[-1]]
                try:
                    subsec = self.get_subsection(self.sep.join(parts[:-1]))
                    return subsec.get(parts[-1], smart_get=smart_get,
                                      expand_subsection_key=True)
                except KeyError:
                    pass
        if smart_get is None:
            smart_get = self.smart_get

        content = Missing()
        if key in self.content:
            content = self.content[key]

        section = Missing()
        if smart_get.includes('section'):
            if key in self.subsections:
                section = self.subsections[key]
            else:
                for subsec in self.subsections.values():
                    if key == subsec.full_name:
                        section = subsec
                        break

        subsec_content = []
        if smart_get.includes('all'):
            for subsec in self.subsections.values():
                try:
                    val = subsec.get(key, smart_get=smart_get,
                                     expand_subsection_key=expand_subsection_key)  # noqa: E501
                    subsec_content.append(val)
                except MissingKeyError:
                    pass

        if self.smart_get_unique:
            total = 0
            if not isinstance(content, Missing):
                total += 1
            if not isinstance(section, Missing):
                total += 1
            total += len(subsec_content)
            if total == 0:
                raise MissingKeyError(f'Key {key} not found')
            elif total > 1:
                raise NonUniqueKeyError(f'Key {key} is not unique. Found '
                                        f'value {content}, section '
                                        f'{section}, and values in '
                                        f'subsections {subsec_content}.')
        if not isinstance(content, Missing):
            return content
        if not isinstance(section, Missing):
            return section
        return subsec_content[0]

    def add_subsection(self, name):
        if isinstance(name, self.__class__):
            ret = name
            ret.parent = self
        else:
            parts = name.split(self.sep)
            parent_name = self.sep.join(parts[:-1])
            if parent_name != "" and parent_name != self.full_name:
                if self.has_subsection(parent_name):
                    subsec = self.get_subsection(parent_name)
                    ret = subsec.add_subsection(parts[-1])
                    return ret
                else:
                    raise ValueError(f'Cannot use section name {name}')
            name = parts[-1]
            ret = Section(name, parent=self)
        name = ret.name
        if name in self.subsections:
            raise ValueError(f'There already exists a subsection {name}.')
        self.subsections[name] = ret
        return ret

    def set_value(self, key, value, allow_subsections=True):
        if isinstance(value, self.__class__):
            if key != value.name:
                if key != self.sep.join([self.full_name, value.name]):
                    raise ValueError("Key and section name have to match")
            self.add_subsection(value)
        else:
            parts = key.split(self.sep)
            if len(parts) > 1:
                subsec_name = self.sep.join(parts[:-1])
                if subsec_name == self.name or subsec_name == self.full_name:
                    self.content[parts[-1]] = value
                    return
                try:
                    subsec = self.get_subsection(subsec_name)
                    subsec.set_value(parts[-1], value)
                except KeyError:
                    self.content[key] = value
            else:
                self.content[key] = value

    def __setitem__(self, key, value):
        self.set_value(key, value)


class ConfigReader(Section):
    def __init__(self, *filepaths, name="toplevel", const_sec="Constants",
                 **kwargs):
        super().__init__(name, **kwargs)
        self.es = ExpressionString()
        parser = ConfigParser()
        for fpath in filepaths:
            parser.read(fpath)
        sections = parser.sections()
        if const_sec in sections:
            for key, val in parser[const_sec].items():
                self.es.register_constant(key, self.es.parse(val))
        section = self
        for sec in sections:
            secname = self.sep + sec
            section = section.add_subsection(secname)
            for key, val in parser[sec].items():
                section[key] = self.es.parse(val)
