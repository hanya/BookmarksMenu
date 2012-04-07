#  Copyright 2012 Tsutomu Uchino
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

class CurrentStringResource(object):
    """ Shared string resource. """
    
    Current = None
    
    def get(ctx):
        klass = CurrentStringResource
        if klass.Current is None:
            from bookmarks import RES_DIR, RES_FILE
            import bookmarks.tools
            klass.Current = bookmarks.tools.get_current_resource(
                ctx, RES_DIR, RES_FILE)
        return klass.Current
    
    get = staticmethod(get)


class Graphics(object):
    """ Keeps graphics. """
    
    Graphics = None
    
    GRAPHIC_DEFS = (
        ("container", "folder_16"), 
        ("document", "document_16"), 
        ("macro", "paper_16"), 
        ("command", "gear_16"), 
        ("program", "command_16"), 
        ("file", "file_16"), 
        ("folder", "open_16"), 
        ("web", "web_16"), 
        ("addthis", "addthis_16"), 
        ("edit", "bookmarks_16"), 
        ("separator", "separator_16"), 
        ("long_separator", "long_separator"), 
        ("directory_popup", "place_16"), 
        ("tag", "tag_16"), 
    )
    
    def get(ctx, high_contrast=False):
        klass = Graphics
        if not klass.Graphics:
            klass.Graphics = klass(ctx, high_contrast)
        return klass.Graphics
    
    get = staticmethod(get)
    
    def __init__(self, ctx, high_contrast=False):
        self.init_graphics(ctx, high_contrast)
    
    def init_graphics(self, ctx, high_contrast=False):
        from com.sun.star.beans import PropertyValue
        from bookmarks import ICONS_DIR
        graphics = {}
        gp = ctx.getServiceManager().createInstanceWithContext(
                "com.sun.star.graphic.GraphicProvider", ctx)
        p = PropertyValue()
        p.Name = "URL"
        for graphic_def in self.GRAPHIC_DEFS:
            if high_contrast:
                p.Value = ICONS_DIR + graphic_def[1] + "_h.png"
            else:
                p.Value = ICONS_DIR + graphic_def[1] + ".png"
            graphics[graphic_def[0]] = gp.queryGraphic((p,))
        self.graphics = graphics
    
    def __getitem__(self, name):
        try:
            return self.graphics[name]
        except:
            return self.graphics["command"]

