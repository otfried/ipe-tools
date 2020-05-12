//
// ipepython.cpp
//
// Python extension module to use Ipelib through Lua.
//
// Based on Gustavo Niemeyer's Lunatic Python bridge.
// http://labix.org/lunatic-python
// 

#include <Python.h>

extern "C" {
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
}

// to include a small table with some info about Ipe configuration
#define IPELUA_CONFIG 0

// for testing direct execution of Lua code, not used for Ipe bindings
#define IPELUA_EVAL 0

#if IPELUA_CONFIG
#include "ipebase.h"
#endif

// --------------------------------------------------------------------

// in ipelua
extern "C" int luaopen_ipe(lua_State *L);

#define POBJECT "POBJECT"

typedef struct {
  PyObject_HEAD
  int ref;
  int refiter;
} LuaObject;

typedef struct
{
    PyObject *o;
    int asindx;
} py_object;

extern PyTypeObject LuaObject_Type;

#define LuaObject_Check(op) PyObject_TypeCheck(op, &LuaObject_Type)

static lua_State *LuaState = nullptr;

// --------------------------------------------------------------------

static int py_convert_custom(lua_State *L, PyObject *o, int asindx)
{
  py_object *obj = (py_object*) lua_newuserdata(L, sizeof(py_object));
  if (!obj)
    luaL_error(L, "failed to allocate userdata object");
  
  Py_INCREF(o);
  obj->o = o;
  obj->asindx = asindx;
  luaL_getmetatable(L, POBJECT);
  lua_setmetatable(L, -2);
  
  return 1;
}

static int py_convert(lua_State *L, PyObject *o)
{
  int ret = 0;
  if (o == Py_None) {
    // Not really needed, but this way we may check for errors with ret == 0.
    lua_pushnil(L);
    ret = 1;
  } else if (o == Py_True) {
    lua_pushboolean(L, 1);
    ret = 1;
  } else if (o == Py_False) {
    lua_pushboolean(L, 0);
    ret = 1;
  } else if (PyUnicode_Check(o) || PyBytes_Check(o)) {
    PyObject *bstr = PyUnicode_AsEncodedString(o, "utf-8", nullptr);
    Py_ssize_t len;
    char *s;
    
    PyErr_Clear();
    PyBytes_AsStringAndSize(bstr ? bstr : o, &s, &len);
    lua_pushlstring(L, s, len);
    if (bstr) Py_DECREF(bstr);
    ret = 1;
  } else if (PyLong_Check(o)) {
    lua_pushnumber(L, (lua_Number)PyLong_AsLong(o));
    ret = 1;
  } else if (PyFloat_Check(o)) {
    lua_pushnumber(L, (lua_Number)PyFloat_AsDouble(o));
    ret = 1;
  } else if (LuaObject_Check(o)) {
    lua_rawgeti(L, LUA_REGISTRYINDEX, ((LuaObject*)o)->ref);
    ret = 1;
  } else {
    int asindx = PyDict_Check(o) || PyList_Check(o) || PyTuple_Check(o);
    ret = py_convert_custom(L, o, asindx);
  }
  return ret;
}

static py_object* luaPy_to_pobject(lua_State *L, int n)
{
  if(!lua_getmetatable(L, n)) return nullptr;
  luaL_getmetatable(L, POBJECT);
  int is_pobject = lua_rawequal(L, -1, -2);
  lua_pop(L, 2);
  
  return is_pobject ? (py_object *) lua_touserdata(L, n) : nullptr;
}

// --------------------------------------------------------------------

static PyObject *LuaObject_New(lua_State *L, int n)
{
  LuaObject *obj = PyObject_New(LuaObject, &LuaObject_Type);
  if (obj) {
    lua_pushvalue(L, n);
    obj->ref = luaL_ref(L, LUA_REGISTRYINDEX);
    obj->refiter = 0;
  }
  return (PyObject*) obj;
}

static PyObject *LuaConvert(lua_State *L, int n)
{
  PyObject *ret = nullptr;

  switch (lua_type(L, n)) {

  case LUA_TNIL:
    Py_INCREF(Py_None);
    ret = Py_None;
    break;
    
  case LUA_TSTRING: {
    size_t len;
    const char *s = lua_tolstring(L, n, &len);
    ret = PyUnicode_FromStringAndSize(s, len);
    if (!ret) {
      PyErr_Clear();
      ret = PyBytes_FromStringAndSize(s, len);
    }
    break;
  }
  case LUA_TNUMBER: {
    lua_Number num = lua_tonumber(L, n);
    if (num != (long)num) {
      ret = PyFloat_FromDouble(num);
    } else {
      ret = PyLong_FromLong((long)num);
    }
    break;
  }
    
  case LUA_TBOOLEAN:
    ret = lua_toboolean(L, n) ? Py_True : Py_False;
    Py_INCREF(ret);
    break;
    
  case LUA_TUSERDATA: {
    py_object *obj = luaPy_to_pobject(L, n);
    
    if (obj) {
      Py_INCREF(obj->o);
      ret = obj->o;
      break;
    }

    // Otherwise go on and handle as custom.
  }
    
  default:
    ret = LuaObject_New(L, n);
    break;
  }
  
  return ret;
}

// --------------------------------------------------------------------

static PyObject *LuaCall(lua_State *L, PyObject *args)
{
  PyObject *ret = nullptr;
  PyObject *arg;
  int nargs, rc, i;
  
  if (!PyTuple_Check(args)) {
    PyErr_SetString(PyExc_TypeError, "tuple expected");
    lua_settop(L, 0);
    return nullptr;
  }
  
  nargs = PyTuple_Size(args);
  for (i = 0; i != nargs; i++) {
    arg = PyTuple_GetItem(args, i);
    if (arg == nullptr) {
      PyErr_Format(PyExc_TypeError,
		   "failed to get tuple item #%d", i);
      lua_settop(L, 0);
      return nullptr;
    }
    rc = py_convert(L, arg);
    if (!rc) {
      PyErr_Format(PyExc_TypeError,
		   "failed to convert argument #%d", i);
      lua_settop(L, 0);
      return nullptr;
    }
  }
  
  if (lua_pcall(L, nargs, LUA_MULTRET, 0) != 0) {
    PyErr_Format(PyExc_Exception,
                 "error: %s", lua_tostring(L, -1));
    return nullptr;
  }
  
  nargs = lua_gettop(L);
  if (nargs == 1) {
    ret = LuaConvert(L, 1);
    if (!ret) {
      PyErr_SetString(PyExc_TypeError,
		      "failed to convert return");
      lua_settop(L, 0);
      Py_DECREF(ret);
      return nullptr;
    }
  } else if (nargs > 1) {
    ret = PyTuple_New(nargs);
    if (!ret) {
      PyErr_SetString(PyExc_RuntimeError,
		      "failed to create return tuple");
      lua_settop(L, 0);
      return nullptr;
    }
    for (i = 0; i != nargs; i++) {
      arg = LuaConvert(L, i+1);
      if (!arg) {
	PyErr_Format(PyExc_TypeError,
		     "failed to convert return #%d", i);
	lua_settop(L, 0);
	Py_DECREF(ret);
	return nullptr;
      }
      PyTuple_SetItem(ret, i, arg);
    }
  } else {
    Py_INCREF(Py_None);
    ret = Py_None;
  }
  
  lua_settop(L, 0);
  
  return ret;
}

// --------------------------------------------------------------------

static int LuaObject_methodCall(lua_State *L)
{
  int n = lua_gettop(L);                 // number of arguments to method call
  lua_pushvalue(L, lua_upvalueindex(2)); // push method
  lua_insert(L, 1);                      // move to bottom of stack
  lua_pushvalue(L, lua_upvalueindex(1)); // push object containing the method
  lua_insert(L, 2);                      // make it the first argument
  lua_call(L, n + 1, LUA_MULTRET);
  return lua_gettop(L);                  // return results
}

// --------------------------------------------------------------------

static void LuaObject_dealloc(LuaObject *self)
{
  luaL_unref(LuaState, LUA_REGISTRYINDEX, self->ref);
  if (self->refiter)
    luaL_unref(LuaState, LUA_REGISTRYINDEX, self->refiter);
  Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *LuaObject_getattr(PyObject *obj, PyObject *attr)
{
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject*)obj)->ref);
  if (lua_isnil(LuaState, -1)) {
    lua_pop(LuaState, 1);
    PyErr_SetString(PyExc_RuntimeError, "lost reference");
    return nullptr;
  }
  
  if (!lua_isstring(LuaState, -1)
      && !lua_istable(LuaState, -1)
      && !lua_isuserdata(LuaState, -1)) {
    lua_pop(LuaState, 1);
    PyErr_SetString(PyExc_RuntimeError, "not an indexable value");
    return nullptr;
  }

  PyObject *ret = nullptr;
  int rc = py_convert(LuaState, attr);
  if (rc) {
    bool byName = lua_type(LuaState, -1) == LUA_TSTRING;
    lua_gettable(LuaState, -2);
    if (byName && lua_type(LuaState, -1) == LUA_TFUNCTION && lua_isuserdata(LuaState, -2)) {
      // We are retrieving a method of an object.
      // Build a closure packing the method with the object itself
      lua_pushcclosure(LuaState, LuaObject_methodCall, 2);
    }
    ret = LuaConvert(LuaState, -1);
  } else {
    PyErr_SetString(PyExc_ValueError, "can't convert attr/key");
  }
  lua_settop(LuaState, 0);
  return ret;
}

static int LuaObject_setattr(PyObject *obj, PyObject *attr, PyObject *value)
{
  int ret = -1;
  int rc;
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject*)obj)->ref);
  if (lua_isnil(LuaState, -1)) {
    lua_pop(LuaState, 1);
    PyErr_SetString(PyExc_RuntimeError, "lost reference");
    return -1;
  }
  if (!lua_istable(LuaState, -1)) {
    lua_pop(LuaState, -1);
    PyErr_SetString(PyExc_TypeError, "Lua object is not a table");
    return -1;
  }
  rc = py_convert(LuaState, attr);
  if (rc) {
    if (nullptr == value) {
      lua_pushnil(LuaState);
      rc = 1;
    } else {
      rc = py_convert(LuaState, value);
    }
    
    if (rc) {
      lua_settable(LuaState, -3);
      ret = 0;
    } else {
      PyErr_SetString(PyExc_ValueError, "can't convert value");
    }
  } else {
    PyErr_SetString(PyExc_ValueError, "can't convert key/attr");
  }
  lua_settop(LuaState, 0);
  return ret;
}

static PyObject *LuaObject_str(PyObject *obj)
{
  PyObject *ret = nullptr;
  const char *s;
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject*)obj)->ref);
  if (luaL_callmeta(LuaState, -1, "__tostring")) {
    s = lua_tostring(LuaState, -1);
    lua_pop(LuaState, 1);
    if (s) ret = PyUnicode_FromString(s);
  }
  if (!ret) {
    int type = lua_type(LuaState, -1);
    switch (type) {
    case LUA_TTABLE:
    case LUA_TFUNCTION:
      ret = PyUnicode_FromFormat("<Lua %s at %p>",
				 lua_typename(LuaState, type),
				 lua_topointer(LuaState, -1));
      break;
      
    case LUA_TUSERDATA:
    case LUA_TLIGHTUSERDATA:
      ret = PyUnicode_FromFormat("<Lua %s at %p>",
				 lua_typename(LuaState, type),
				 lua_touserdata(LuaState, -1));
      break;
      
    case LUA_TTHREAD:
      ret = PyUnicode_FromFormat("<Lua %s at %p>",
				 lua_typename(LuaState, type),
				 (void*)lua_tothread(LuaState, -1));
      break;
      
    default:
      ret = PyUnicode_FromFormat("<Lua %s>",
				 lua_typename(LuaState, type));
      break;
      
    }
  }
  lua_pop(LuaState, 1);
  return ret;
}

static int LuaObject_pcmp(lua_State *L)
{
  int op = lua_tointeger(L, -3);
  switch(op) {
  case Py_EQ:
    lua_pushboolean(L, lua_compare(L, -2, -1, LUA_OPEQ));
    break;
  case Py_NE:
    lua_pushboolean(L, !lua_compare(L, -2, -1, LUA_OPEQ));
    break;
  case Py_GT:
    lua_insert(LuaState, -2);  // flip order of arguments
  case Py_LT:
    lua_pushboolean(L, lua_compare(L, -2, -1, LUA_OPLT));
    break;
  case Py_GE:
    lua_insert(LuaState, -2);
  case Py_LE:
    lua_pushboolean(L, lua_compare(L, -2, -1, LUA_OPLE));
  }
  return 1;
}

static PyObject* LuaObject_richcmp(PyObject *lhs, PyObject *rhs, int op)
{
  if (!LuaObject_Check(rhs)) return Py_False;

  lua_pushcfunction(LuaState, LuaObject_pcmp);
  lua_pushinteger(LuaState, op);
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject *)lhs)->ref);
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject *)rhs)->ref);
  if (lua_pcall(LuaState, 3, 1, 0) != LUA_OK) {
    PyErr_SetString(PyExc_RuntimeError, lua_tostring(LuaState, -1));
    return nullptr;
  }
  return lua_toboolean(LuaState, -1) ? Py_True : Py_False;
}

static PyObject *LuaObject_call(PyObject *obj, PyObject *args)
{
  lua_settop(LuaState, 0);
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject*)obj)->ref);
  return LuaCall(LuaState, args);
}

static PyObject *LuaObject_iternext(LuaObject *obj)
{
  PyObject *ret = nullptr;
  
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject*)obj)->ref);

  // refuse to iterate on anything except tables, as we haven't implemented it
  if (lua_type(LuaState, -1) != LUA_TTABLE)
    return nullptr;
  
  if (obj->refiter == 0)
    lua_pushnil(LuaState);
  else
    lua_rawgeti(LuaState, LUA_REGISTRYINDEX, obj->refiter);

  if (lua_next(LuaState, -2) != 0) {
    // Remove value.
    lua_pop(LuaState, 1);
    ret = LuaConvert(LuaState, -1);
    // Save key for next iteration.
    if (!obj->refiter)
      obj->refiter = luaL_ref(LuaState, LUA_REGISTRYINDEX);
    else
      lua_rawseti(LuaState, LUA_REGISTRYINDEX, obj->refiter);
  } else if (obj->refiter) {
    luaL_unref(LuaState, LUA_REGISTRYINDEX, obj->refiter);
    obj->refiter = 0;
  }
  
  return ret;
}

// --------------------------------------------------------------------

static int LuaObject_length(LuaObject *obj)
{
  int len;
  lua_rawgeti(LuaState, LUA_REGISTRYINDEX, ((LuaObject*)obj)->ref);
  len = luaL_len(LuaState, -1);
  lua_settop(LuaState, 0);
  return len;
}

static PyObject *LuaObject_subscript(PyObject *obj, PyObject *key)
{
  return LuaObject_getattr(obj, key);
}

static int LuaObject_ass_subscript(PyObject *obj, PyObject *key, PyObject *value)
{
  return LuaObject_setattr(obj, key, value);
}

static PyMappingMethods LuaObject_as_mapping = {
  (lenfunc)LuaObject_length,              /* mp_length */
  (binaryfunc)LuaObject_subscript,        /* mp_subscript */
  (objobjargproc)LuaObject_ass_subscript, /* mp_ass_subscript */
};

// --------------------------------------------------------------------

static int LuaObject_parith(lua_State *L)
{
  int op = lua_tointeger(L, -1);
  lua_pop(L, 1); // remove op
  lua_arith(LuaState, op);
  return 1;
}

static PyObject *LuaObject_arith(int op, PyObject *lhs, PyObject *rhs)
{
  lua_pushcfunction(LuaState, LuaObject_parith);

  if (!(py_convert(LuaState, lhs) && (rhs == nullptr || py_convert(LuaState, rhs)))) {
    PyErr_SetString(PyExc_TypeError, "failed to convert argument");
    lua_settop(LuaState, 0);
    return nullptr;
  }
  
  lua_pushinteger(LuaState, op);
  if (lua_pcall(LuaState, rhs == nullptr ? 2 : 3, 1, 0) != LUA_OK) {
    PyErr_SetString(PyExc_RuntimeError, lua_tostring(LuaState, -1));
    return nullptr;
  }
  return LuaConvert(LuaState, -1);
}

static PyObject *LuaObject_add(PyObject *lhs, PyObject *rhs)
{
  return LuaObject_arith(LUA_OPADD, lhs, rhs);
}

static PyObject *LuaObject_subtract(PyObject *lhs, PyObject *rhs)
{
  return LuaObject_arith(LUA_OPSUB, lhs, rhs);
}

static PyObject *LuaObject_multiply(PyObject *lhs, PyObject *rhs)
{
  return LuaObject_arith(LUA_OPMUL, lhs, rhs);
}

static PyObject *LuaObject_power(PyObject *lhs, PyObject *rhs)
{
  return LuaObject_arith(LUA_OPPOW, lhs, rhs);
}

static PyObject *LuaObject_negative(PyObject *rhs)
{
  return LuaObject_arith(LUA_OPUNM, rhs, nullptr);
}

static PyNumberMethods LuaObject_as_number = {
  (binaryfunc) LuaObject_add, /* nb_add */
  (binaryfunc) LuaObject_subtract, /* nb_subtract */
  (binaryfunc) LuaObject_multiply, /* nb_multiply */
  nullptr, /* nb_remainder */
  nullptr, /* nb_divmod */
  nullptr, /* nb_power */
  (unaryfunc) LuaObject_negative, /* nb_negative */
  nullptr, /* nb_positive */
  nullptr, /* nb_absolute */
  nullptr, /* nb_bool */
  nullptr, /* nb_invert */
  nullptr, /* nb_lshift */
  nullptr, /* nb_rshift */
  nullptr, /* nb_and */
  (binaryfunc) LuaObject_power, /* nb_xor */
  nullptr, /* nb_or */
  nullptr, /* nb_int */
  nullptr, /* nb_reserved */
  nullptr, /* nb_float */
  
  nullptr, /* nb_inplace_add */
  nullptr, /* nb_inplace_subtract */
  nullptr, /* nb_inplace_multiply */
  nullptr, /* nb_inplace_remainder */
  nullptr, /* nb_inplace_power */
  nullptr, /* nb_inplace_lshift */
  nullptr, /* nb_inplace_rshift */
  nullptr, /* nb_inplace_and */
  nullptr, /* nb_inplace_xor */
  nullptr, /* nb_inplace_or */
  
  nullptr, /* nb_floor_divide */
  nullptr, /* nb_true_divide */
  nullptr, /* nb_inplace_floor_divide */
  nullptr, /* nb_inplace_true_divide */
  
  nullptr, /* nb_index */
  
  nullptr, /* nb_matrix_multiply */
  nullptr, /* nb_inplace_matrix_multiply */
};

// --------------------------------------------------------------------

PyTypeObject LuaObject_Type = {
  PyVarObject_HEAD_INIT(nullptr, 0)
  "lua.custom",             /*tp_name*/
  sizeof(LuaObject),        /*tp_basicsize*/
  0,                        /*tp_itemsize*/
  (destructor)LuaObject_dealloc, /*tp_dealloc*/
  0,                        /*tp_print*/
  0,                        /*tp_getattr*/
  0,                        /*tp_setattr*/
  0,                        /*tp_compare*/
  LuaObject_str,            /*tp_repr*/
  &LuaObject_as_number,     /*tp_as_number*/
  0,                        /*tp_as_sequence*/
  &LuaObject_as_mapping,    /*tp_as_mapping*/
  0,                        /*tp_hash*/
  (ternaryfunc)LuaObject_call, /*tp_call*/
  LuaObject_str,            /*tp_str*/
  LuaObject_getattr,        /*tp_getattro*/
  LuaObject_setattr,        /*tp_setattro*/
  0,                        /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
  "custom lua object",      /*tp_doc*/
  0,                        /*tp_traverse*/
  0,                        /*tp_clear*/
  LuaObject_richcmp,        /*tp_richcompare*/
  0,                        /*tp_weaklistoffset*/
  PyObject_SelfIter,        /*tp_iter*/
  (iternextfunc)LuaObject_iternext, /*tp_iternext*/
  0,                        /*tp_methods*/
  0,                        /*tp_members*/
  0,                        /*tp_getset*/
  0,                        /*tp_base*/
  0,                        /*tp_dict*/
  0,                        /*tp_descr_get*/
  0,                        /*tp_descr_set*/
  0,                        /*tp_dictoffset*/
  0,                        /*tp_init*/
  PyType_GenericAlloc,      /*tp_alloc*/
  PyType_GenericNew,        /*tp_new*/
  PyObject_Del,             /*tp_free*/
  0,                        /*tp_is_gc*/
};

// --------------------------------------------------------------------

#if IPELUA_EVAL
static PyObject *Lua_run(PyObject *args, int eval)
{
  char *s;
  int len;
  
  if (!PyArg_ParseTuple(args, "s#", &s, &len))
    return nullptr;
  
  char *buf = nullptr;
  
  if (eval) {
    buf = (char *) malloc(strlen("return ")+len+1);
    strcpy(buf, "return ");
    strncat(buf, s, len);
    s = buf;
    len = strlen("return ")+len;
  }
  
  if (luaL_loadbuffer(LuaState, s, len, "<python>") != 0) {
    PyErr_Format(PyExc_RuntimeError,
                 "error loading code: %s",
                 lua_tostring(LuaState, -1));
    free(buf);
    return nullptr;
  }
  
  free(buf);
  
  if (lua_pcall(LuaState, 0, 1, 0) != 0) {
    PyErr_Format(PyExc_RuntimeError,
                 "error executing code: %s",
                 lua_tostring(LuaState, -1));
    return nullptr;
  }
  
  PyObject *ret = LuaConvert(LuaState, -1);
  lua_settop(LuaState, 0);
  return ret;
}

static PyObject *Lua_execute(PyObject *self, PyObject *args)
{
  return Lua_run(args, 0);
}

static PyObject *Lua_eval(PyObject *self, PyObject *args)
{
  return Lua_run(args, 1);
}

static PyObject *Lua_globals(PyObject *self, PyObject *args)
{
  PyObject *ret = nullptr;
  lua_getglobal(LuaState, "_G");
  if (lua_isnil(LuaState, -1)) {
    PyErr_SetString(PyExc_RuntimeError, "lost globals reference");
    lua_pop(LuaState, 1);
    return nullptr;
  }
  ret = LuaConvert(LuaState, -1);
  if (!ret)
    PyErr_Format(PyExc_TypeError, "failed to convert table");
  lua_settop(LuaState, 0);
  return ret;
}
#endif

// --------------------------------------------------------------------

static PyMethodDef ipe_methods[] =
{
#if IPELUA_EVAL
  {"execute",    Lua_execute,    METH_VARARGS, nullptr},
  {"eval",       Lua_eval,       METH_VARARGS, nullptr},
  {"globals",    Lua_globals,    METH_NOARGS,  nullptr},
#endif
  {nullptr,      nullptr}
};

static struct PyModuleDef ipelua_module = {
  PyModuleDef_HEAD_INIT,
  "ipe",
  "Ipelib interface through Python-Lua bridge",
  -1,
  ipe_methods
};

// --------------------------------------------------------------------

#if IPELUA_CONFIG
static void push_string(lua_State *L, ipe::String str)
{
  lua_pushlstring(L, str.data(), str.size());
}

static void setup_config(lua_State *L)
{
  lua_getglobal(L, "ipe");
  
  lua_newtable(L);  // config table

  push_string(L, ipe::Platform::latexDirectory());
  lua_setfield(L, -2, "latexdir");

  lua_pushinteger(L, ipe::IPELIB_VERSION);
  lua_setfield(L, -2, "version");

  lua_setfield(L, -2, "config");  // set as ipe.config
  lua_pop(L, 1);
}
#endif

static bool populate_module(PyObject *m, lua_State *L)
{
  lua_getglobal(L, "ipe");
  lua_pushnil(L);
  while (lua_next(L, -2) != 0) {
    PyObject *obj = LuaConvert(L, -1);
    lua_pop(L, 1);
    if (obj == nullptr || lua_type(L, -1) != LUA_TSTRING) 
      return false;
    Py_INCREF(obj);
    if (PyModule_AddObject(m, lua_tostring(L, -1), obj) < 0) {
      Py_DECREF(m);
      Py_DECREF(obj);
      return false;
    }
  }
  return true;
}

// --------------------------------------------------------------------

PyMODINIT_FUNC PyInit_ipe(void)
{
  PyObject *m;
  if (PyType_Ready(&LuaObject_Type) < 0 ||
      (m = PyModule_Create(&ipelua_module)) == nullptr)
    return nullptr;

  if (!LuaState) {
    LuaState = luaL_newstate();
    luaL_openlibs(LuaState);
    luaopen_ipe(LuaState);
#if IPELUA_CONFIG
    setup_config(LuaState);
#endif
    bool ok = populate_module(m, LuaState);
    lua_settop(LuaState, 0);
    if (!ok) return nullptr;
  }
  return m;
}

// --------------------------------------------------------------------
