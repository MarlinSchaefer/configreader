# ConfigReader

An easy-to-use and powerful configuration-file reader. It allows for
safe constant definitions and function invocations from the config-file,
supports arbitrarily many sub-sections, and an easy interface to grab
values from the config-file.

## Install
Clone the contents of this repository
`git clone https://github.com/MarlinSchaefer/configreader.git`
and install it using pip
`pip install .`

## Usage
This config reader is based on the `ConfigParser` from the Python standard
library. As such it supports the same syntax. However, it builds on top of it,
by introducing sub-sections, a dynamic type inference, the ability to handle
function calls in the config-file and a simple way to access the contents.

To start import the config file (see the contents of this file below)
```python
from configreader import ConfigReader
config = ConfigReader('example.ini', name='Config')
```
You can then print the contents of this file
```python
print(config)
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
```
Values with unique names can be accessed directly from the top level without
needing to navigate or specify the subsection
```python
config['sampler_name']
'custom'
```
Other parameters can be accessed in different ways
```python
config['Sampler/parameter1/min']
0
config['Sampler']['parameter1']['min']
0
```
You can also see, that the types from the config file were automatically
inferred and the function call `sin` was executed, using the known constant
`pi`. Also the constant `c` defined in the `Constants` section was used to
calculate the value of `Sampler/parameter2/max`.


## example.ini
```
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
max = sin(pi / 4)

[/parameter2]
min = -1
max = c / 2
```