typedef struct DestructorChain {
    struct DestructorChain* next;
    void* destructor;
    void* object;
} DestructorChain;

#define ATEXIT_FUNC_MAX 64

DestructorChain* __global_destructor_chain;
static int atexit_curr_func;
static DestructorChain atexit_funcs[ATEXIT_FUNC_MAX];

void* __register_global_object(void* object, void* destructor, void* regmem) {
    ((DestructorChain*)regmem)->next = __global_destructor_chain;
    ((DestructorChain*)regmem)->destructor = destructor;
    ((DestructorChain*)regmem)->object = object;
    __global_destructor_chain = (DestructorChain*)regmem;
    return object;
}

void __destroy_global_chain(void) {
    DestructorChain* iter;

    while ((iter = __global_destructor_chain) != 0) {
        __global_destructor_chain = iter->next;
        ((void (*)(void*, short))iter->destructor)(iter->object, -1);
    }
}

int __register_atexit(void (*func)(void)) {
    if (atexit_curr_func == ATEXIT_FUNC_MAX) {
        return -1;
    }

    __register_global_object(0, func, &atexit_funcs[atexit_curr_func++]);
    return 0;
}
