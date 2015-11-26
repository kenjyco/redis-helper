Redis Helper
============

> Helper functions to store/retrieve redis objects.

## Install

```
% pip install git+git://github.com/kenjyco/redis_helper.git
```

## Usage

> TODO

## Background

[dict]: https://docs.python.org/2/tutorial/datastructures.html#dictionaries
[hash]: http://redis.io/commands#hash

A [Python dictionary][dict] is a very useful **container** for grouping facts
about some particular entity/object. Dictionaries have **keys** that map to
**values**, so if we want to retrieve a particular value stored in a dictionary,
we can access it through its key.

> It's common to work with a **collection** of dictionary objects that are
> related in some way (a list of dictionaries for example). When your program
> stops, the dictionary objects created by the program go away.

Redis is a **data structure server** (among other things). It is great for
storing various types of objects that can be accessed between different programs
and processes. When your program stops, objects that you have stored in Redis
will remain.

A [Redis hash][hash] is most similar to a Python dictionary.
