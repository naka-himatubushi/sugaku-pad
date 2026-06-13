//
//  埋め込み CPython 初期化 + mathai 呼び出し（C API）。
//  初期化は BeeWare Python-Apple-support の testbed(PyConfig 隔離設定)を踏襲。
//  バンドル構成: Resources/python(PYTHONHOME) / app(自前) / app_packages(sympy)。
//
#import "PythonBridge.h"
#import <Python/Python.h>

@implementation PythonBridge

static BOOL gReady = NO;

+ (BOOL)startup {
    if (gReady) return YES;

    NSString *res = [[NSBundle mainBundle] resourcePath];
    NSString *home = [NSString stringWithFormat:@"%@/python", res];

    PyStatus status;
    PyPreConfig preconfig;
    PyConfig config;

    // 隔離設定（環境変数やユーザ site を無視）。UTF-8 を強制。
    PyPreConfig_InitIsolatedConfig(&preconfig);
    preconfig.utf8_mode = 1;
    status = Py_PreInitialize(&preconfig);
    if (PyStatus_Exception(status)) {
        NSLog(@"[PythonBridge] preinit 失敗: %s", status.err_msg);
        return NO;
    }

    PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;   // 署名済みバンドルには書けないので .pyc を作らない
    config.buffered_stdio = 0;   // ログ即時化

    wchar_t *whome = Py_DecodeLocale([home UTF8String], NULL);
    status = PyConfig_SetString(&config, &config.home, whome);
    PyMem_RawFree(whome);
    if (PyStatus_Exception(status)) {
        NSLog(@"[PythonBridge] PYTHONHOME 設定失敗: %s", status.err_msg);
        PyConfig_Clear(&config);
        return NO;
    }

    status = PyConfig_Read(&config);
    if (PyStatus_Exception(status)) {
        NSLog(@"[PythonBridge] site config 読込失敗: %s", status.err_msg);
        PyConfig_Clear(&config);
        return NO;
    }

    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        NSLog(@"[PythonBridge] 初期化失敗: %s", status.err_msg);
        return NO;
    }

    // 自前コード(app) と依存(app_packages) を sys.path の先頭へ
    PyObject *sysPath = PySys_GetObject("path");  // borrowed
    for (NSString *sub in @[@"app", @"app_packages"]) {
        NSString *p = [NSString stringWithFormat:@"%@/%@", res, sub];
        PyObject *u = PyUnicode_FromString([p UTF8String]);
        PyList_Insert(sysPath, 0, u);
        Py_DECREF(u);
    }

    gReady = YES;
    return YES;
}

+ (NSString *)solveJSON:(NSString *)latex {
    if (![self startup]) return @"{\"supported\":false,\"kind\":\"error\",\"error\":\"python init failed\",\"steps\":[],\"answer\":[]}";

    NSString *out = @"{\"supported\":false,\"kind\":\"error\",\"error\":\"call failed\",\"steps\":[],\"answer\":[]}";
    PyObject *mod = PyImport_ImportModule("bridge");
    if (mod) {
        PyObject *fn = PyObject_GetAttrString(mod, "solve_json");
        if (fn && PyCallable_Check(fn)) {
            PyObject *arg = PyUnicode_FromString([latex UTF8String]);
            PyObject *r = PyObject_CallFunctionObjArgs(fn, arg, NULL);
            if (r) {
                const char *s = PyUnicode_AsUTF8(r);
                if (s) out = [NSString stringWithUTF8String:s];
                Py_DECREF(r);
            } else {
                PyErr_Print();
            }
            Py_XDECREF(arg);
        }
        Py_XDECREF(fn);
        Py_DECREF(mod);
    } else {
        PyErr_Print();
        out = @"{\"supported\":false,\"kind\":\"error\",\"error\":\"import bridge failed\",\"steps\":[],\"answer\":[]}";
    }
    return out;
}

@end
