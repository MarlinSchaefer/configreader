import ast
import math
import io
import os
from collections import OrderedDict
from configparser import ConfigParser


class ExpressionString(object):
    """A class to safely parse strings into Python datatypes. It also allows to
    specify constants and functions that are allowed to be parsed.
    
    Arguments
    ---------
    constants : {None or iterable of 2-tuples, None}
        An iterable of 2-tuples, where the first entry of every tuple is the
        name given to the constant and the second value is the value.
        
    functions : {None or iterable, None}
        An iterable containing functions that should be allowed to be parsed.
        The entries may either be 2-tuples or individual callables. If an
        individual callable is given, its name will be used as key. If
        2-tuples are given, the first entry is expected to contain the name
        by which the function should be parsed from strings and the second
        entry is expected to be the callable.
    
    Notes
    -----
    The following functions are supported out of the box:
        -sin: math.sin
        -cos: math.cos
        -tan: math.tan
        -exp: math.exp
        -root: math.sqrt
        -sqrt: math.sqrt
        -sum: sum (built-in)
        -int: int (built-in)
        -float: float (built-in)
        -bool: bool (built-in)
        -str: str (built-in)
    
    The following constants are supported out of the box:
        -pi: 3.141592653589793
        -Pi: 3.141592653589793
        -PI: 3.141592653589793
        -e: 2.718281828459045
        -E: 2.718281828459045
    
    Usage
    -----
    >>> expstr = ExpressionString()
    >>> expstr("1+1")
    2
    >>> expstr("[1, 2]")
    [1, 2]
    >>> expstr("sin(2*pi)")
    -2.4492935982947064e-16
    >>> expstr("{'foo': 'bar', 'baz': 2.7}")
    {'foo': 'bar', 'baz': 2.7}
    >>> type(expstr("True"))
    <class 'bool'>
    """
    def __init__(self, constants=None, functions=None):
        self.functions = {'sin': math.sin,
                          'cos': math.cos,
                          'tan': math.tan,
                          'exp': math.exp,
                          'root': math.sqrt,
                          'sqrt': math.sqrt,
                          'sum': sum,
                          'int': int,
                          'float': float,
                          'bool': bool,
                          'str': str}
        self.constants = {'pi': math.pi,
                          'Pi': math.pi,
                          'PI': math.pi,
                          'e': math.e,
                          'E': math.e}
        if constants is not None:
            for key, val in constants:
                self.register_constant(key, val)
        
        if functions is not None:
            for item in functions:
                try:
                    name, func = item
                except TypeError:
                    name = None
                    func = item
                self.register_function(func, name=name)

    def register_function(self, func, name=None):
        """Register a function to be parsed by the ExpressionString.
        
        Arguments
        ---------
        func : callable
            The function that should be executed.
        name . {None or str, None}
            The name by which the function is called. If None, func.__name__
            will be used.
        
        Notes
        -----
        If a function with the same name exists already, it will be
        overwritten without a warning.
        """
        if callable(func):
            if name is None:
                name = func.__name__
            self.functions[name] = func

    def register_constant(self, name, val):
        """Register a constant that should be parsed.
        
        Arguments
        ---------
        name : str
            The name of the constant that should be searched for during
            parsing.
        val : object
            The value that should be used for the constant.
        
        Notes
        -----
        If a constant with the same name exists already, it will be
        overwritten without a warning.
        """
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
        elif isinstance(node.op, ast.Pow):
            op = 'pow'
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
        """Parse a string into Python datatypes.
        
        Arguments
        ---------
        string : str
            The string that should be parsed.
        
        Returns
        -------
        object
            The parsed Python object.
        
        Notes
        -----
        The function uses the ast (abstract-syntax tree) module under the
        hood. This module converts the string into a tree-structure, that
        contains different objects. To extend the syntax allowed by this
        class, create a sub-class. If an object from the syntax tree cannot be
        handled by the ExpressionString (i.e. a ValueError(`Forbidden node`)
        is raised), you can add it by creating a class parse_ClassName. This
        function should then handle the conversion from ast-object to Python
        object.
        """
        tree = ast.parse(string)
        return self.parse_node(tree)

    def __call__(self, string):
        return self.parse(string)


class Missing(object):
    def __str__(self):
        return "Missing"

    def __repr__(self):
        "Missing()"


class MissingKeyError(KeyError):
    pass


class NonUniqueKeyError(KeyError):
    pass


class MissingSubsectionError(KeyError):
    pass


class Section(object):
    """An object to reprent a section in a configuration file. May be the root.
    
    Arguments
    ---------
    name : str
        The name of the section.
    parent : {None or Section, None}
        The section which this section is a subsection of. If None, it is
        interpreted as the root.
    sep : {str, '/'}
        The separator used to differentiate between sections and subsections.
    content : {None or dict}
        The key-value pairs stored in this section.
    """
    def __init__(self, name, parent=None, sep='/', content=None):
        self.name = name
        self.sep = sep
        self.content = content if content is not None else {}
        self.parent = parent
        self.subsections = OrderedDict()

    @property
    def full_path(self):
        if self.parent is None:
            return self.name
        else:
            return f'{self.parent.full_path}{self.sep}{self.name}'

    def expand_sublevel(self, key):
        """Expand a key to a full path. Replace leading separators by the
        correct section and sub-section names, starting at the top-level.
        
        If `key` is a single string, that does not contain the separator, the
        key is expanded to the full path of this section with the key as a
        sub-section.
        
        All leading separators are expanded into the appropriate sub-sections.
        The first non-separator is used as the break point, from which the key
        is assumed to give a valid path.
        
        Arguments
        ---------
        key : str
            The key that should be expanded.
        
        Returns
        -------
        path
            Path to the sub-level.
        
        Example
        -------
        Structure of the config:
        toplevel
         └─sub1
            └─sub2
        
        >>> toplevel = Section("toplevel", sep="/")
        >>> sub1 = toplevel.add_subsection("sub1")
        >>> sub2 = sub1.add_subsection("sub2")
        >>> sub2.expand_sublevel('sub3')
        'toplevel/sub1/sub2/sub3'
        >>> sub2.expand_sublevel("/sub1.2")
        'toplevel/sub1.2'
        >>> sub2.expand_sublevel("//sub2.2")
        'toplevel/sub1/sub2.2'
        >>> sub2.expand_sublevel("///sub3")
        'toplevel/sub1/sub2/sub3'
        >>> sub2.expand_sublevel("/sub1.2/sub2.2")
        'toplevel/sub1.2/sub2.2'
        """
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
        """Convert a key into a full path, using expand_sublevel, and split
        it into the parts that already exist and the parts that are missing.
        
        Arguments
        ---------
        key : str
            The key that should be checked for existing and missing
            sub-sections.
        
        Returns
        -------
        exist : list
            A list of strings that provides the names in order of appearance
            from the toplevel that do exist.
        missing: list
            A list of strings that provides the names in order of appearence
            from the toplevel that do not exist.
        
        Example
        -------
        Structure of the config:
        toplevel
         └─sub1
            └─sub2
        
        >>> toplevel = Section("toplevel", sep="/")
        >>> sub1 = toplevel.add_subsection("sub1")
        >>> sub2 = sub1.add_subsection("sub2")
        >>> sub2.split_exist('sub3')
        (['toplevel', 'sub1', 'sub2'], ['sub3'])
        >>> sub2.split_exist("/sub1.2")
        (['toplevel'], ['sub1.2'])
        >>> sub2.split_exist("//sub2.2")
        (['toplevel', 'sub1'], ['sub2.2'])
        >>> sub2.split_exist("///sub3")
        sub2.split_exist("///sub3")
        >>> sub2.split_exist("/sub1.2/sub2.2")
        (['toplevel'], ['sub1.2', 'sub2.2'])
        """
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
        """Check if the sub-section specified by the key is a first-level
        sub-section of this section.
        
        Arguments
        ---------
        name : str
            Key to check. The key is expanded using `expand_sublevel`.
        
        Returns
        -------
        bool :
            Whether or not the key specifies a direct sub-section of this
            section.
        """
        name = self.expand_sublevel(name)
        name = name.split(self.sep)[-1]
        return name in self.subsections

    def find_subsections(self, name):
        """Recursively find all sub-sections of this section with the given
        name.
        
        Arguments
        ---------
        name : str
            Name of the sub-section that is being searched for.
        
        Returns
        -------
        list :
            List of full paths to the sub-sections with the given name.
        """
        ret = []
        for subsec in self.subsections.values():
            if name == subsec.name:
                ret.append(subsec.full_path)
            ret.extend(subsec.find_subsections(name))
        return ret

    def is_subsection(self, name):
        """Check if this section has a sub-section with the given name.
        
        Arguments
        ---------
        name : str
            Name of the subsection to check.
        
        Returns
        -------
        bool :
            Returns True if there is a sub-section with the given name.
        """
        subsecs = self.find_subsections(name)
        return len(subsecs) > 0

    def get_from_path(self, path):
        """Obtain a section or value from a complete path. A path is a string,
        where different sub-sections are separated by the separator.
        
        Arguments
        ---------
        path : str
            The path from which to return the value or sub-section. Values
            are preferred over sub-sections of the same name.
        
        Returns
        -------
        object or Section :
            Returns the value or Section specified by the path.
        
        Raises
        ------
        ValueError :
            Raises a ValueError if the path does not start at the toplevel of
            this section.
        
        MissingKeyError :
            Raises a MissingKeyError if the path does not point to a value or
            Section.
        """
        section = self.toplevel
        parts = path.split(self.sep)
        topname = parts.pop(0)
        if section.name != topname:
            raise ValueError(f'Invalid path {path}.')
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
        """Add one or multiple sub-sections to this Section.
        
        Arguments
        ---------
        name : str
            The key at which to add the sub-section. This value is expanded
            using `expand_sublevel`. All missing sub-sections are added in
            order.
        squeeze : {bool, True}
            If only a single Section is added, return the Section instead of a
            list containing that single Section.
        
        Returns
        -------
        list or Section :
            Returns a list of all the Sections that were created in order. If
            `squeeze` is True and the list contains only a single element,
            that single element will be returned.
        """
        exists, missing = self.split_exist(name)
        section = self.get_from_path(self.sep.join(exists + ['']))
        ret = []
        for mname in missing:
            tmp = Section(mname, parent=section, sep=self.sep)
            section.subsections[mname] = tmp
            section = tmp
            ret.append(tmp)
        if squeeze and len(ret) == 1:
            return ret[0]
        else:
            return ret

    def find_values(self, name, squeeze=True):
        """Find all values in the config with the given name.
        
        Arguments
        ---------
        name : str
            The name of the value to search for.
        squeeze : {bool, True}
            If only a single value with the name is found, return that value
            instead of a dictionary of which the value is the only entry.
        
        Returns
        -------
        dict or object:
            Returns a dictionary containing the full paths to the sub-sections
            the value is part of as keys and the value as the corresponding
            value. If only a single entry is in the dicitionary and `squuze`
            is True, only the value will be returned.
        int :
            The number of values that were found.
        """
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
        """Find a single value of the given name. Raises an Error if multiple
        values of the same name are found. Also raises an Error if no value
        with the given name is found.
        
        Arguments
        ---------
        name : str
            The name to search for.
        
        Returns
        -------
        object :
            The value of the given name.
        
        Raises
        ------
        MissingKeyError :
            Raises a MissingKeyError if the key is not found in the Section.
        NonUniqueKeyError :
            Raises a NonUniqueKeyError if there are multiple value of the same
            name.
        """
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
        """Add a value to the given section.
        
        Arguments
        ---------
        key : str
            The key for the value that should be added. It is expanded using
            `expand_sublevel`, which means that also values in other Sections
            may be set this way. (If the key is string that does not contain
            the separator, it will be added to this Section)
        value : object
            The value to add.
        
        Raises
        ------
        MissingSubsectionError :
            Raises a MissingSubsectionError if the value should be set in a
            sub-section that is not yet created.
        """
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
        """Retrieve values or Sections.
        
        Arguments
        ---------
        key : str
            Key of which to retrieve the value or Section from. This key is
            expanded using `expand_sublevel`. The key has to be unique
        
        Returns
        -------
        object or Section
            The object or section that was retrieved.
        """
        if self.sep not in key:
            vals, n = self.find_values(key, squeeze=False)
            secs = self.find_subsections(key)
            secs = [self.get_from_path(sec + self.sep) for sec in secs]
            for sec in secs:
                keypath = self.sep.join(sec.full_path.split(self.sep)[:-1])
                keypath += '/'
                vals[keypath] = sec
            total = n + len(secs)
            if total == 0:
                raise MissingKeyError(f'No value or section with key {key}.')
            if total > 1:
                direct_children = {}
                for keypth, val in vals.items():
                    if keypth.endswith('/') and keypth[:-1] == self.full_path:
                        direct_children[keypath] = val
                    elif keypth == self.full_path:
                        direct_children[keypth] = val
                    
                if len(direct_children) > 1 or len(direct_children) == 0:
                    err_sec = [sec.full_path for sec in secs]
                    raise NonUniqueKeyError('Found multiple values: '
                                            f'{list(vals.values())} and '
                                            'sections: '
                                            f'{err_sec}')
                else:
                    vals = direct_children
            if n == 0:
                return secs[0]
            else:
                return next(iter(vals.values()))
        else:
            key = self.expand_sublevel(key)
            return self.get_from_path(key)

    def sections(self):
        """Get a list of all direct subsections of this Section.
        """
        return list(self.subsections.keys())
    
    def to_dict(self, from_toplevel=False):
        """Return a dictionary that contains the information of this Section
        and all its subsections.
        
        Arguments
        ---------
        from_toplevel : {bool, False}
            Get the dictionary from the root Section.
        
        Returns
        -------
        dict :
            The dictionary containing the information of the Section and all
            its subsections.
        """
        if from_toplevel:
            return self.toplevel.to_dict(from_toplevel=False)
        
        ret = self.content.copy()
        for sec in self.sections():
            section = self[sec]
            ret[sec] = section.to_dict(from_toplevel=False)
        return ret
    
    def get_lines(self, level=0):
        """Recursive helper function to print the Section.
        """
        ret = [(self.name + self.sep, level)]
        for sec in self.sections():
            section = self.subsections[sec]
            ret.extend(section.get_lines(level=level+1))
        for key, val in self.content.items():
            ret.append((f'{key} = {val}', level+1))
        return ret
    
    def __str__(self):
        """String representation of the Section.
        """
        straigh_down = ' │ '
        corner = ' └─'
        down_right = ' ├─'
        lines = self.get_lines()
        maxlevel = max([pt[1] for pt in lines], default=0)
        to_print = [['   ' for _ in range((maxlevel + 1))]
                    for _ in range(len(lines))]
        for i, (name, level) in enumerate(lines):
            to_print[i][level] = corner
            for j in reversed(range(i)):
                prev_level = lines[j][1]
                if prev_level > level:
                    to_print[j][level] = straigh_down
                elif prev_level == level:
                    to_print[j][level] = down_right
                    break
                elif level > prev_level:
                    break
        
        to_print = to_print[1:]
        to_print = [pt[1:] for pt in to_print]
        for i, (name, level) in enumerate(lines[1:]):
            to_print[i][level-1] += name
        ret = f'{lines[0][0]}\n'
        ret += '\n'.join([''.join(pt).rstrip() for pt in to_print])
        return ret


class ConfigReader(Section):
    """A configuration file reader that allows for safe function execution and
    interpreting the values as Python data types.
    
    Arguments
    ---------
    *filepaths : str
        Path(s) to the configuration files that should be read.
    name : {str, 'toplevel'}
        The name of the toplevel Section.
    const_sec : {str, 'Constants'}
        The section in the configuration files from which constants are used
        in the remaining sections. Set to None if no constants should be used
        from the configuration files.
    **kwargs :
        All other keyword arguments are passed to the Section constructor.
    
    Example
    -------
    Consider the configuration file
    [Constants]
    c = 3 * 10 ** 8
    
    [detectors]
    width = 2
    [/det1]
    height = 1.5
    
    [/det2]
    height = 2
    
    [Sampler]
    sampler_name = custom
    [/parameter1]
    min = 0
    max = sin(pi / 2)
    
    [/parameter2]
    min = -1
    max = c / 2
    
    >>> from configreader import ConfigReader
    >>> config = ConfigReader(/path/to/config, name="Config")
    >>> print(config)
    Config/
     ├─Constants/
     │  └─c = 300000000
     ├─detectors/
     │  ├─det1/
     │  │  └─height = 1.5
     │  ├─det2/
     │  │  └─height = 2
     │  └─width = 2
     └─Sampler/
        ├─parameter1/
        │  ├─min = 0
        │  └─max = 0.7071067811865475
        ├─parameter2/
        │  ├─min = -1
        │  └─max = 150000000.0
        └─sampler_name = custom
    
    The config-reader exposes a simple interface to read values. For unqiue
    values, the simple name is enough, irrespective of what sub-section it is
    in. Otherwise a specific key can be used.
    
    >>> config["sampler_name"]
    'custom'
    >>> config["Sampler/sampler_name"]
    'custom'
    >>> config["detectors/det1/height"]
    1.5
    >>> config["Sampler/parameter1/min"]
    0
    >>> config["Sampler"]["parameter1"]["min"]
    0
    """
    def __init__(self, *filepaths, name="toplevel", const_sec="Constants",
                 **kwargs):
        super().__init__(name, **kwargs)
        self.es = ExpressionString()
        parser = ConfigParser()
        for fpath in filepaths:
            if isinstance(fpath, io.IOBase):
                parser.read_file(fpath)
            elif os.path.exists(fpath):
                parser.read(fpath)
            else:
                parser.read_string(fpath)
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
