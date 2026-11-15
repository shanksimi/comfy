def get_detailer_options(hook):
    getter = getattr(hook, "get_detailer_options", None)
    return getter() if getter is not None else {}


def get_detailer_detection_hook(hook):
    kind = type(hook).__name__
    if kind == "AdvancedOptionsDetailerHook":
        return None
    if kind == "DetailerHookCombine":
        first = get_detailer_detection_hook(hook.hook1)
        second = get_detailer_detection_hook(hook.hook2)
        if first is None:
            return second
        if second is None:
            return first
    return hook
