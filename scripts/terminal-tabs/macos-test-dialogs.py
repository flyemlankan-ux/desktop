#!/usr/bin/env python3
"""Owned-process macOS Accessibility helpers. Never requests permissions; input is restricted to an explicit test PID."""
import ctypes as C
import os
import time

class AccessibilityError(RuntimeError): pass

class OwnedAppDialogs:
    """Inspect/press real controls only beneath one test application's AX root."""
    def __init__(self, pid):
        if not isinstance(pid,int) or pid <= 1: raise ValueError('A live test-owned PID is required')
        os.kill(pid,0)
        self.pid=pid;self.refs=[];self.errors=[]
        self.ax=C.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        self.cf=C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.cg=C.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
        def bind(lib,name,args,ret):
            fn=getattr(lib,name);fn.argtypes=args;fn.restype=ret;return fn
        P=C.c_void_p;I=C.c_int;L=C.c_long
        bind(self.ax,'AXIsProcessTrusted',[],C.c_bool)
        if not self.ax.AXIsProcessTrusted(): raise AccessibilityError('Accessibility permission is not already granted. No permission request was made.')
        bind(self.ax,'AXUIElementCreateApplication',[I],P)
        bind(self.ax,'AXUIElementGetPid',[P,C.POINTER(I)],I)
        bind(self.ax,'AXUIElementCopyAttributeValue',[P,P,C.POINTER(P)],I)
        bind(self.ax,'AXUIElementPerformAction',[P,P],I)
        bind(self.ax,'AXUIElementSetAttributeValue',[P,P,P],I)
        bind(self.cf,'CFStringCreateWithCString',[P,C.c_char_p,C.c_uint32],P)
        bind(self.cf,'CFStringGetCString',[P,C.c_char_p,L,C.c_uint32],C.c_bool)
        for name in ['CFStringGetTypeID','CFArrayGetTypeID','CFBooleanGetTypeID']:
            bind(self.cf,name,[],C.c_ulong)
        bind(self.cf,'CFGetTypeID',[P],C.c_ulong)
        bind(self.cf,'CFArrayGetCount',[P],L)
        bind(self.cf,'CFArrayGetValueAtIndex',[P,L],P)
        bind(self.cf,'CFBooleanGetValue',[P],C.c_bool)
        bind(self.cf,'CFRetain',[P],P);bind(self.cf,'CFRelease',[P],None)
        bind(self.cg,'CGEventCreateKeyboardEvent',[P,C.c_ushort,C.c_bool],P)
        bind(self.cg,'CGEventSetFlags',[P,C.c_uint64],None)
        bind(self.cg,'CGEventKeyboardSetUnicodeString',[P,C.c_ulong,C.POINTER(C.c_ushort)],None)
        bind(self.cg,'CGEventPostToPid',[I,P],None)
        self.root=self.ax.AXUIElementCreateApplication(pid);self.refs.append(self.root)
    def close(self):
        for ref in reversed(self.refs):self.cf.CFRelease(ref)
        self.refs=[]
    def string(self,text):return self.cf.CFStringCreateWithCString(None,text.encode('utf-8'),0x08000100)
    def owner(self,element):
        pid=C.c_int();error=self.ax.AXUIElementGetPid(element,C.byref(pid))
        if error or pid.value!=self.pid:raise AccessibilityError(f'Refusing UI element outside test PID {self.pid}: error={error}, owner={pid.value}')
    def attr(self,element,name):
        self.owner(element);key=self.string(name);value=C.c_void_p()
        try:error=self.ax.AXUIElementCopyAttributeValue(element,key,C.byref(value))
        finally:self.cf.CFRelease(key)
        if error or not value.value:
            if error:self.errors=(self.errors+[{'attribute':name,'error':error}])[-30:]
            return None
        ptr=value.value
        try:
            kind=self.cf.CFGetTypeID(ptr)
            if kind==self.cf.CFStringGetTypeID():
                buf=C.create_string_buffer(32768)
                return buf.value.decode('utf-8') if self.cf.CFStringGetCString(ptr,buf,len(buf),0x08000100) else ''
            if kind==self.cf.CFBooleanGetTypeID():return bool(self.cf.CFBooleanGetValue(ptr))
            if kind==self.cf.CFArrayGetTypeID():
                out=[]
                for i in range(self.cf.CFArrayGetCount(ptr)):
                    child=self.cf.CFArrayGetValueAtIndex(ptr,i);self.cf.CFRetain(child);self.refs.append(child);out.append(child)
                return out
            self.cf.CFRetain(ptr);self.refs.append(ptr);return ptr
        finally:self.cf.CFRelease(ptr)
    def tree(self,max_nodes=1800):
        for ref in self.refs[1:]:self.cf.CFRelease(ref)
        self.refs=self.refs[:1]
        seen=set();count=0
        def visit(element,depth):
            nonlocal count
            if not element or element in seen or depth>28:return None
            seen.add(element);count+=1
            if count>max_nodes:raise AccessibilityError('Owned accessibility tree exceeded bounded scan')
            self.owner(element)
            node={'element':element,'role':self.attr(element,'AXRole'),'title':self.attr(element,'AXTitle'),'description':self.attr(element,'AXDescription'),'value':self.attr(element,'AXValue'),'enabled':self.attr(element,'AXEnabled'),'children':[]}
            # AXWindows is necessary at the app root; children are used below.
            children=(self.attr(element,'AXWindows') or self.attr(element,'AXChildren')) if depth==0 else self.attr(element,'AXChildren')
            for child in children or []:
                item=visit(child,depth+1)
                if item:node['children'].append(item)
            return node
        return visit(self.root,0)
    @staticmethod
    def flatten(node):
        yield node
        for child in node['children']:yield from OwnedAppDialogs.flatten(child)
    @staticmethod
    def text(node):
        return '\n'.join(str(n.get(k) or '') for n in OwnedAppDialogs.flatten(node) for k in ['title','description','value'] if isinstance(n.get(k),str))
    def press(self,element):
        self.owner(element)
        if self.attr(element,'AXRole')!='AXButton':raise AccessibilityError('Expected actual AXButton')
        if self.attr(element,'AXEnabled') is False:raise AccessibilityError('Button is disabled; not overriding it')
        action=self.string('AXPress')
        try:error=self.ax.AXUIElementPerformAction(element,action)
        finally:self.cf.CFRelease(action)
        if error:raise AccessibilityError(f'AXPress failed ({error})')
    def dialog_button(self,labels,required_text,timeout=15):
        end=time.monotonic()+timeout;last=[]
        while time.monotonic()<end:
            tree=self.tree();scopes=[n for n in self.flatten(tree) if n['role'] in {'AXSheet','AXDialog','AXWindow'} and required_text.lower() in self.text(n).lower()]
            # Prefer the smallest actual modal-containing window/sheet; never
            # choose an identically named button from a different test window.
            scopes.sort(key=lambda n:sum(1 for _ in self.flatten(n)))
            for scope in scopes:
                buttons=[n for n in self.flatten(scope) if n['role']=='AXButton' and n['enabled'] is not False]
                last=[(n['title'],n['description']) for n in buttons]
                matches=[n for n in buttons if n['title'] in labels or n['description'] in labels]
                if len(matches)==1:return matches[0]['element']
            time.sleep(.1)
        raise AccessibilityError(f'No unique enabled {labels} button in owned dialog containing {required_text!r}; buttons={last}; frontmost={self.attr(self.root, "AXFrontmost")}; hidden={self.attr(self.root, "AXHidden")}; children={len(self.attr(self.root, "AXChildren") or [])}; AXerrors={self.errors[-8:]}')
    def press_dialog_button(self,labels,required_text,timeout=15):
        element=self.dialog_button(labels,required_text,timeout);self.press(element)
    def key(self,keycode,flags=0):
        """Send one key to the explicit test PID, never the globally focused app."""
        self.owner(self.root);os.kill(self.pid,0)
        for down in (True,False):
            event=self.cg.CGEventCreateKeyboardEvent(None,keycode,down)
            try:self.cg.CGEventSetFlags(event,flags);self.cg.CGEventPostToPid(self.pid,event)
            finally:self.cf.CFRelease(event)
    def type_text(self,text):
        self.owner(self.root);os.kill(self.pid,0)
        encoded=text.encode('utf-16-le');units=(C.c_ushort*(len(encoded)//2)).from_buffer_copy(encoded)
        for down in (True,False):
            event=self.cg.CGEventCreateKeyboardEvent(None,0,down)
            try:self.cg.CGEventKeyboardSetUnicodeString(event,len(units),units);self.cg.CGEventPostToPid(self.pid,event)
            finally:self.cf.CFRelease(event)
    def enter_picker_folder(self,path):
        """Normal Cmd+Shift+G, literal path and Return, all posted to test PID."""
        if not os.path.isabs(path) or not os.path.isdir(path):raise ValueError('Existing absolute synthetic folder required')
        self.dialog_button(['Cancel'],'Choose starting folder') # Own visible picker required first.
        self.key(5,(1<<20)|(1<<17)) # G with Command and Shift
        # Read the genuinely focused input only after the owned native sheet
        # received the shortcut. Never type into a background Settings field.
        end=time.monotonic()+10
        while time.monotonic()<end:
            focused=self.attr(self.root,'AXFocusedUIElement')
            if focused and self.attr(focused,'AXRole') in {'AXTextField','AXComboBox'}:
                description=' '.join(str(self.attr(focused,k) or '') for k in ['AXTitle','AXDescription','AXHelp'])
                if 'folder' in description.lower() or 'path' in description.lower():break
            time.sleep(.1)
        else:raise AccessibilityError('A labelled Go to Folder input did not gain focus')
        self.key(0,1<<20) # Command+A within test PID
        self.type_text(path);self.key(36) # Return navigates the real picker.
        time.sleep(.35) # UI transition only; returned field path is verified by caller.

    def activate(self):
        """Normal foreground activation of the owned app, not an AX permission change."""
        self.owner(self.root)
        key=self.string('AXFrontmost')
        value=C.c_void_p.in_dll(self.cf,'kCFBooleanTrue').value
        try:error=self.ax.AXUIElementSetAttributeValue(self.root,key,value)
        finally:self.cf.CFRelease(key)
        if error:raise AccessibilityError(f'Owned app activation failed ({error})')
        end=time.monotonic()+10
        while time.monotonic()<end:
            if self.attr(self.root,'AXWindows'):return
            time.sleep(.1)
        raise AccessibilityError('Owned app has no exposed native windows after activation')

    def raise_window(self):
        focused=self.attr(self.root,'AXFocusedWindow')
        if not focused:raise AccessibilityError('No owned focused window')
        self.owner(focused);action=self.string('AXRaise')
        try:error=self.ax.AXUIElementPerformAction(focused,action)
        finally:self.cf.CFRelease(action)
        if error:raise AccessibilityError(f'Owned window AXRaise failed ({error})')

    def owned_window_id(self,bounds,expected=None):
        """Read window metadata only; retain no other app's metadata or imagery."""
        self.owner(self.root);os.kill(self.pid,0)
        P=C.c_void_p
        listing=self.cg.CGWindowListCopyWindowInfo;listing.argtypes=[C.c_uint32,C.c_uint32];listing.restype=P
        get=self.cf.CFDictionaryGetValue;get.argtypes=[P,P];get.restype=P
        number=self.cf.CFNumberGetValue;number.argtypes=[P,C.c_int,P];number.restype=C.c_bool
        def field(dictionary,name):
            key=self.string(name)
            try:return get(dictionary,key)
            finally:self.cf.CFRelease(key)
        def numeric(value):
            if not value:raise AccessibilityError('Missing required CG window field')
            result=C.c_double()
            if not number(value,13,C.byref(result)):raise AccessibilityError('Invalid CG window number')
            return result.value
        # Only on-screen windows for initial resolution; exact ID thereafter.
        windows=listing(8 if expected is not None else 1,expected or 0)
        if not windows:raise AccessibilityError('No CG window metadata available')
        candidates=[]
        try:
            for i in range(self.cf.CFArrayGetCount(windows)):
                item=self.cf.CFArrayGetValueAtIndex(windows,i)
                if numeric(field(item,'kCGWindowOwnerPID'))!=self.pid:continue
                window_id=int(numeric(field(item,'kCGWindowNumber')))
                if expected is not None and window_id!=expected:continue
                if numeric(field(item,'kCGWindowLayer'))!=0:continue
                rectangle=field(item,'kCGWindowBounds')
                actual=[numeric(field(rectangle,key)) for key in ['X','Y','Width','Height']]
                if all(abs(a-b)<=2 for a,b in zip(actual,bounds)):candidates.append(window_id)
        finally:self.cf.CFRelease(windows)
        if len(candidates)!=1:raise AccessibilityError('Owned CG window ID absent or ambiguous; refusing pointer input')
        return candidates[0]

    def drag(self,start,end,bounds,duration=.8,annotate_window=False):
        """Real mouse sequence to one PID; points must come from owned DOM+window geometry."""
        x,y,width,height=bounds
        if width<=0 or height<=0:raise ValueError('Owned window bounds required')
        for px,py in [start,end]:
            if not (x<=px<=x+width and y<=py<=y+height):raise ValueError('Refusing mouse point outside supplied test-window bounds')
        class Point(C.Structure):_fields_=[('x',C.c_double),('y',C.c_double)]
        create=self.cg.CGEventCreateMouseEvent;create.argtypes=[C.c_void_p,C.c_uint32,Point,C.c_uint32];create.restype=C.c_void_p
        self.raise_window()
        window_id=self.owned_window_id(bounds) if annotate_window else None
        set_field=self.cg.CGEventSetIntegerValueField;set_field.argtypes=[C.c_void_p,C.c_uint32,C.c_int64];set_field.restype=None
        def post(kind,point):
            self.owner(self.root);os.kill(self.pid,0)
            event=create(None,kind,Point(*point),0)
            if not event:raise AccessibilityError('Could not construct owned mouse event')
            try:
                if window_id is not None:
                    if kind != 2:  # Always release within the same PID if geometry changes.
                        self.owned_window_id(bounds,expected=window_id)
                    # Public Apple fields: click count, window under pointer,
                    # window able to handle event. No global HID posting.
                    for field,value in [(1,1),(91,window_id),(92,window_id),(40,self.pid)]:
                        set_field(event,field,value)
                self.cg.CGEventPostToPid(self.pid,event)
            finally:self.cf.CFRelease(event)
        post(5,start);post(1,start)
        try:
            for step in range(1,25):
                point=(start[0]+(end[0]-start[0])*step/24,start[1]+(end[1]-start[1])*step/24)
                post(6,point);time.sleep(duration/24)
        finally:post(2,end)
        return window_id
