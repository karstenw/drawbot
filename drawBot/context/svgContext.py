import objc
import AppKit
import CoreText

import os
# import base64
import random
import uuid

from fontTools.misc.xmlWriter import XMLWriter

from fontTools.misc.transform import Transform

from tools.openType import getFeatureTagsForFontAttributes
from baseContext import BaseContext, GraphicsState, Shadow, Color, FormattedString, Gradient

from drawBot.misc import warnings, formatNumber


# simple file object


class SVGFile(object):

    optimize = False

    def __init__(self):
        self._svgdata = []

    def write(self, value):
        self._svgdata.append(value)

    def writeToFile(self, path):
        data = self.read()
        f = open(path, "w")
        f.write(data)
        f.close()

    def read(self):
        return "".join(self._svgdata)

    def close(self):
        pass


# subclass some object to add some svg api


class SVGColor(Color):

    def svgColor(self):
        c = self.getNSObject()
        if c:
            if c.numberOfComponents() == 2:
                # gray number
                r = g = b = int(255*c.whiteComponent())
            else:
                try:
                    red = c.redComponent()
                except (AttributeError,ValueError), err:
                    c = c.colorUsingColorSpaceName_(AppKit.NSCalibratedRGBColorSpace)
                r = int(255 * c.redComponent())
                g = int(255 * c.greenComponent())
                b = int(255 * c.blueComponent())
            a = c.alphaComponent()
            return "rgba(%s,%s,%s,%s)" % (r, g, b, a)
        return None


class SVGGradient(Gradient):

    _colorClass = SVGColor

    def __init__(self, *args, **kwargs):
        objc.super(SVGGradient, self).__init__(*args, **kwargs)
        self.tagID = uuid.uuid4().hex

    def copy(self):
        new = objc.super(SVGShadow, self).copy()
        new.tagID = self.tagID
        return new

    def writeDefs(self, ctx):
        ctx.begintag("defs")
        ctx.newline()
        self._writeFilter(ctx)
        ctx.endtag("defs")
        ctx.newline()

    def _writeFilter(self, ctx):
        if self.gradientType == "linear":
            self._writeLinear(ctx)
            self._writeLinear(ctx, flipped=True)
        elif self.gradientType == "radial":
            self._writeRadial(ctx)
            self._writeRadial(ctx, flipped=True)

    def _writeLinear(self, ctx, flipped=False):
        x1, y1 = self.start
        x2, y2 = self.end
        tagID = self.tagID
        if flipped:
            tagID = "%s_flipped" % tagID
            y1 = ctx.height - y1
            y2 = ctx.height - y2
        ctx.begintag("linearGradient", id=tagID, x1=x1, y1=y1, x2=x2, y2=y2, gradientUnits="userSpaceOnUse")
        ctx.newline()
        for i, color in enumerate(self.colors):
            position = self.positions[i]
            stopData = {"offset": position, "stop-color": color.svgColor()}
            ctx.simpletag("stop", **stopData)
            ctx.newline()
        ctx.endtag("linearGradient")
        ctx.newline()

    def _writeRadial(self, ctx, flipped=False):
        x1, y1 = self.start
        x2, y2 = self.end
        tagID = self.tagID
        if flipped:
            tagID = "%s_flipped" % tagID
            y1 = ctx.height - y1
            y2 = ctx.height - y2
        ctx.begintag("radialGradient", id=tagID, cx=x2, cy=y2, r=self.endRadius, fx=x1, fy=y1, gradientUnits="userSpaceOnUse")
        ctx.newline()
        for i, color in enumerate(self.colors):
            position = self.positions[i]
            stopData = {"offset": position, "stop-color": color.svgColor()}
            ctx.simpletag("stop", **stopData)
            ctx.newline()
        ctx.endtag("radialGradient")
        ctx.newline()


class SVGShadow(Shadow):

    _colorClass = SVGColor

    def __init__(self, *args, **kwargs):
        objc.super(SVGShadow, self).__init__(*args, **kwargs)
        self.tagID = uuid.uuid4().hex

    def copy(self):
        new = objc.super(SVGShadow, self).copy()
        new.tagID = self.tagID
        return new

    def writeDefs(self, ctx):
        ctx.begintag("defs")
        ctx.newline()
        self._writeFilter(ctx)
        self._writeFilter(ctx, flipped=True)
        ctx.endtag("defs")
        ctx.newline()

    def _writeFilter(self, ctx, flipped=False):
        tagID = self.tagID
        if flipped:
            tagID = "%s_flipped" % tagID
        ctx.begintag("filter", id=tagID, x="-500%", y="-500%", width="1000%", height="1000%")
        ctx.newline()
        if self.blur < 0:
            self.blur = 0
        blurData = {"in": "SourceAlpha", "stdDeviation": "%f" % self.blur}
        ctx.simpletag("feGaussianBlur", **blurData)
        ctx.newline()
        dx, dy = self.offset
        if flipped:
            dy *= -1
        offsetData = {"dx": dx, "dy": dy, "result": "offsetblur"}
        ctx.simpletag("feOffset", **offsetData)
        ctx.newline()
        colorData = {"flood-color": self.color.svgColor()}
        ctx.simpletag("feFlood", **colorData)
        ctx.newline()
        ctx.simpletag("feComposite", in2="offsetblur", operator="in")
        ctx.newline()
        ctx.begintag("feMerge")
        ctx.newline()
        ctx.simpletag("feMergeNode")
        ctx.newline()
        feMergeNodeData = {"in": "SourceGraphic"}
        ctx.simpletag("feMergeNode", **feMergeNodeData)
        ctx.newline()
        ctx.endtag("feMerge")
        ctx.newline()
        ctx.endtag("filter")
        ctx.newline()


class SVGGraphicsState(GraphicsState):

    _colorClass = SVGColor

    def __init__(self):
        objc.super(SVGGraphicsState, self).__init__()
        self.transformMatrix = Transform(1, 0, 0, 1, 0, 0)
        self.clipPathID = None

    def copy(self):
        new = objc.super(SVGGraphicsState, self).copy()
        new.transformMatrix = Transform(*self.transformMatrix[:])
        new.clipPathID = self.clipPathID
        return new


class SVGContext(BaseContext):

    _graphicsStateClass = SVGGraphicsState
    _shadowClass = SVGShadow
    _colorClass = SVGColor
    _gradientClass = SVGGradient

    _svgFileClass = SVGFile

    _svgTagArguments = {
        "version": "1.1",
        "xmlns": "http://www.w3.org/2000/svg",
        }

    _svgLineJoinStylesMap = {
                    AppKit.NSMiterLineJoinStyle: "miter",
                    AppKit.NSRoundLineJoinStyle: "round",
                    AppKit.NSBevelLineJoinStyle: "bevel"
                    }

    _svgLineCapStylesMap = {
        AppKit.NSButtLineCapStyle: "butt",
        AppKit.NSSquareLineCapStyle: "square",
        AppKit.NSRoundLineCapStyle: "round",
    }

    indentation = " "
    fileExtensions = ["svg"]

    def __init__(self):
        objc.super(SVGContext, self).__init__()
        self._pages = []

    # not supported in a svg context

    def cmykFill(self, c, m, y, k, a=1):
        warnings.warn("cmykFill is not supported in a svg context")

    def cmykStroke(self, c, m, y, k, a=1):
        warnings.warn("cmykStroke is not supported in a svg context")

    def cmykLinearGradient(self, startPoint=None, endPoint=None, colors=None, locations=None):
        warnings.warn("cmykLinearGradient is not supported in a svg context")

    def cmykRadialGradient(self, startPoint=None, endPoint=None, colors=None, locations=None, startRadius=0, endRadius=100):
        warnings.warn("cmykRadialGradient is not supported in a svg context")

    def cmykShadow(self, offset, blur, color):
        warnings.warn("cmykShadow is not supported in a svg context")

    # svg overwrites

    def shadow(self, offset, blur, color):
        objc.super(SVGContext, self).shadow(offset, blur, color)
        if self._state.shadow is not None:
            self._state.shadow.writeDefs(self._svgContext)

    def linearGradient(self, startPoint=None, endPoint=None, colors=None, locations=None):
        objc.super(SVGContext, self).linearGradient(startPoint, endPoint, colors, locations)
        if self._state.gradient is not None:
            self._state.gradient.writeDefs(self._svgContext)

    def radialGradient(self, startPoint=None, endPoint=None, colors=None, locations=None, startRadius=0, endRadius=100):
        objc.super(SVGContext, self).radialGradient(startPoint, endPoint, colors, locations, startRadius, endRadius)
        if startRadius != 0:
            warnings.warn("radialGradient will clip the startRadius to '0' in a svg context.")
        if self._state.gradient is not None:
            self._state.gradient.writeDefs(self._svgContext)

    # svg

    def _reset(self, other=None):
        self._embeddedFonts = set()

    def _newPage(self, width, height):
        if hasattr(self, "_svgContext"):
            self._svgContext.endtag("svg")
        self.reset()
        self.size(width, height)
        self._svgData = self._svgFileClass()
        self._pages.append(self._svgData)
        self._svgContext = XMLWriter(self._svgData, encoding="utf-8", indentwhite=self.indentation)
        self._svgContext.width = self.width
        self._svgContext.height = self.height
        self._svgContext.begintag("svg", width=self.width, height=self.height, **self._svgTagArguments)
        self._svgContext.newline()
        self._state.transformMatrix = self._state.transformMatrix.scale(1, -1).translate(0, -self.height)

    def _saveImage(self, path, multipage):
        if multipage is None:
            multipage = False
        self._svgContext.endtag("svg")
        fileName, fileExt = os.path.splitext(path)
        firstPage = 0
        pageCount = len(self._pages)
        pathAdd = "_1"
        if not multipage:
            firstPage = pageCount - 1
            pathAdd = ""
        for index in range(firstPage, pageCount):
            page = self._pages[index]
            svgPath = fileName + pathAdd + fileExt
            page.writeToFile(svgPath)
            pathAdd = "_%s" % (index + 2)

    def _save(self):
        pass

    def _restore(self):
        pass

    def _drawPath(self):
        if self._state.path:
            self._svgBeginClipPath()
            data = self._svgDrawingAttributes()
            data["d"] = self._svgPath(self._state.path)
            data["transform"] = self._svgTransform(self._state.transformMatrix)
            if self._state.shadow is not None:
                data["filter"] = "url(#%s)" % self._state.shadow.tagID
            if self._state.gradient is not None:
                data["fill"] = "url(#%s)" % self._state.gradient.tagID
            self._svgContext.simpletag("path", **data)
            self._svgContext.newline()
            self._svgEndClipPath()

    def _clipPath(self):
        uniqueID = self._getUniqueID()
        self._svgContext.begintag("clipPath", id=uniqueID)
        self._svgContext.newline()
        data = dict()
        data["d"] = self._svgPath(self._state.path)
        data["transform"] = self._svgTransform(self._state.transformMatrix)
        data["clip-rule"] = "evenodd"
        self._svgContext.simpletag("path", **data)
        self._svgContext.newline()
        self._svgContext.endtag("clipPath")
        self._svgContext.newline()
        self._state.clipPathID = uniqueID

    def _textBox(self, txt, box, align):
        path, (x, y) = self._getPathForFrameSetter(box)
        canDoGradients = True
        if align == "justified":
            warnings.warn("justified text is not supported in a svg context")
        attrString = self.attributedString(txt, align=align)
        if self._state.hyphenation:
            attrString = self.hyphenateAttributedString(attrString, path)
        txt = attrString.string()
        setter = CoreText.CTFramesetterCreateWithAttributedString(attrString)
        box = CoreText.CTFramesetterCreateFrame(setter, (0, 0), path, None)

        self._svgBeginClipPath()
        defaultData = self._svgDrawingAttributes()

        data = {
            "text-anchor": "start",
            "transform": self._svgTransform(self._state.transformMatrix.translate(x, y + self.height).scale(1, -1))
            }
        if self._state.shadow is not None:
            data["filter"] = "url(#%s_flipped)" % self._state.shadow.tagID
        self._svgContext.begintag("text", **data)
        self._svgContext.newline()

        ctLines = CoreText.CTFrameGetLines(box)
        origins = CoreText.CTFrameGetLineOrigins(box, (0, len(ctLines)), None)
        for i, (originX, originY) in enumerate(origins):
            ctLine = ctLines[i]
            # bounds = CoreText.CTLineGetImageBounds(ctLine, self._pdfContext)
            # if bounds.size.width == 0:
            #     continue
            ctRuns = CoreText.CTLineGetGlyphRuns(ctLine)
            for ctRun in ctRuns:
                stringRange = CoreText.CTRunGetStringRange(ctRun)
                attributes = CoreText.CTRunGetAttributes(ctRun)
                font = attributes.get(AppKit.NSFontAttributeName)
                fontAttributes = font.fontDescriptor().fontAttributes()
                fillColor = attributes.get(AppKit.NSForegroundColorAttributeName)
                strokeColor = attributes.get(AppKit.NSStrokeColorAttributeName)
                strokeWidth = attributes.get(AppKit.NSStrokeWidthAttributeName, self._state.strokeWidth)
                baselineShift = attributes.get(AppKit.NSBaselineOffsetAttributeName, 0)
                openTypeFeatures = fontAttributes.get(CoreText.NSFontFeatureSettingsAttribute)

                fontName = font.fontName()
                fontSize = font.pointSize()

                spanData = dict(defaultData)
                fill = self._colorClass(fillColor).svgColor()
                if fill:
                    spanData["fill"] = fill
                stroke = self._colorClass(strokeColor).svgColor()
                if stroke:
                    spanData["stroke"] = stroke
                    spanData["stroke-width"] = formatNumber(abs(strokeWidth))
                spanData["font-family"] = fontName
                spanData["font-size"] = formatNumber(fontSize)

                if openTypeFeatures:
                    featureTags = getFeatureTagsForFontAttributes(openTypeFeatures)
                    spanData["style"] = self._svgStyle(**{
                            "font-feature-settings": self._svgStyleOpenTypeFeatures(featureTags)
                        }
                    )

                if canDoGradients and self._state.gradient is not None:
                    spanData["fill"] = "url(#%s_flipped)" % self._state.gradient.tagID

                self._save()

                runTxt = txt.substringWithRange_((stringRange.location, stringRange.length))
                while runTxt and runTxt[-1] == " ":
                    runTxt = runTxt[:-1]
                runTxt = runTxt.replace("\n", "")
                runTxt = runTxt.encode("utf-8")

                runPos = CoreText.CTRunGetPositions(ctRun, (0, 1), None)
                runX = runY = 0
                if runPos:
                    runX = runPos[0].x
                    runY = runPos[0].y

                spanData["x"] = formatNumber(originX + runX)
                spanData["y"] = formatNumber(self.height - originY - runY + baselineShift)
                self._svgContext.begintag("tspan", **spanData)
                self._svgContext.newline()
                self._svgContext.write(runTxt)
                self._svgContext.newline()
                self._svgContext.endtag("tspan")
                self._svgContext.newline()
                self._restore()

        self._svgContext.endtag("text")
        self._svgContext.newline()
        self._svgEndClipPath()

    def _image(self, path, (x, y), alpha, pageNumber):
        # todo:
        # support embedding of images when the source is not a path but
        # a nsimage or a pdf / gif with a pageNumber
        self._svgBeginClipPath()
        if path.startswith("http"):
            url = AppKit.NSURL.URLWithString_(path)
        else:
            url = AppKit.NSURL.fileURLWithPath_(path)
        im = AppKit.NSImage.alloc().initByReferencingURL_(url)
        w, h = im.size()
        data = dict()
        data["x"] = 0
        data["y"] = 0
        data["width"] = w
        data["height"] = h
        data["opacity"] = alpha
        data["transform"] = self._svgTransform(self._state.transformMatrix.translate(x, y + h).scale(1, -1))
        data["xlink:href"] = path
        self._svgContext.simpletag("image", **data)
        self._svgContext.newline()
        self._svgEndClipPath()

    def _transform(self, transform):
        self._state.transformMatrix = self._state.transformMatrix.transform(transform)

    # helpers

    def _getUniqueID(self):
        return uuid.uuid4().hex
        # b = [chr(random.randrange(256)) for i in range(16)]
        # i = long(('%02x'*16) % tuple(map(ord, b)), 16)
        # return '%032x' % i

    def _svgTransform(self, transform):
        return "matrix(%s)" % (",".join([str(s) for s in transform]))

    def _svgPath(self, path, transformMatrix=None):
        path = path.getNSBezierPath()
        if transformMatrix:
            path = path.copy()
            aT = AppKit.NSAffineTransform.transform()
            aT.setTransformStruct_(transformMatrix[:])
            path.transformUsingAffineTransform_(aT)
        svg = ""
        for i in range(path.elementCount()):
            instruction, points = path.elementAtIndex_associatedPoints_(i)
            if instruction == AppKit.NSMoveToBezierPathElement:
                svg += "M%s,%s " % (formatNumber(points[0].x), formatNumber(points[0].y))
                previousPoint = points[-1]
            elif instruction == AppKit.NSLineToBezierPathElement:
                x = points[0].x - previousPoint.x
                y = points[0].y - previousPoint.y
                svg += "l%s,%s " % (formatNumber(x), formatNumber(y))
                previousPoint = points[-1]
            elif instruction == AppKit.NSCurveToBezierPathElement:
                offx1 = points[0].x - previousPoint.x
                offy1 = points[0].y - previousPoint.y
                offx2 = points[1].x - previousPoint.x
                offy2 = points[1].y - previousPoint.y
                x = points[2].x - previousPoint.x
                y = points[2].y - previousPoint.y
                svg += "c%s,%s,%s,%s,%s,%s " % (formatNumber(offx1), formatNumber(offy1), formatNumber(offx2), formatNumber(offy2), formatNumber(x), formatNumber(y))
                previousPoint = points[-1]
            elif instruction == AppKit.NSClosePathBezierPathElement:
                svg += "Z "
        return svg

    def _svgBeginClipPath(self):
        if self._state.clipPathID:
            data = dict()
            data["clip-path"] = "url(#%s)" % self._state.clipPathID
            self._svgContext.begintag("g", **data)
            self._svgContext.newline()

    def _svgEndClipPath(self):
        if self._state.clipPathID:
            self._svgContext.endtag("g")
            self._svgContext.newline()

    def _svgDrawingAttributes(self):
        data = dict()
        fill = self._svgFillColor()
        if fill:
            data["fill"] = fill
        stroke = self._svgStrokeColor()
        if stroke:
            data["stroke"] = stroke
            data["stroke-width"] = formatNumber(abs(self._state.strokeWidth))
        if self._state.lineDash:
            data["stroke-dasharray"] = ",".join([str(i) for i in self._state.lineDash])
        if self._state.lineJoin in self._svgLineJoinStylesMap:
            data["stroke-linejoin"] = self._svgLineJoinStylesMap[self._state.lineJoin]
        if self._state.lineCap in self._svgLineCapStylesMap:
            data["stroke-linecap"] = self._svgLineCapStylesMap[self._state.lineCap]
        return data

    def _svgFillColor(self):
        if self._state.fillColor:
            return self._state.fillColor.svgColor()
        return None

    def _svgStrokeColor(self):
        if self._state.strokeColor:
            return self._state.strokeColor.svgColor()
        return None

    def _svgStyleOpenTypeFeatures(self, featureTags):
        return ", ".join(["'%s'" % tag for tag in featureTags])

    def _svgStyle(self, **kwargs):
        style = []
        if self._state.blendMode is not None:
            style.append("mix-blend-mode: %s;" % self._state.blendMode)
        for key, value in kwargs.items():
            style.append("%s: %s;" % (key, value))
        return " ".join(style)

    def installFont(self, path):
        success, error = super(self.__class__, self).installFont(path)
        # if path not in self._embeddedFonts:
        #     warnings.warn("Your font will be embedded and accessibele")
        #     self._embeddedFonts.add(path)

        #     f = open(path, "r")
        #     fontData = f.read()
        #     f.close()
        #     fontName = self._fontNameForPath(path)

        #     ctx = self._svgContext
        #     ctx.begintag("defs")
        #     ctx.newline()
        #     ctx.begintag("style", type="text/css")
        #     ctx.newline()
        #     ctx.write("@font-face {")
        #     ctx.newline()
        #     ctx.indent()
        #     ctx.write("font-family: %s;" % fontName)
        #     ctx.newline()
        #     if path.startswith("http"):
        #         ctx.write("src: url(%s');" % path)
        #     else:
        #         ctx.write("src: url('data:application/font-woff;charset=utf-8;base64,%s');" % base64.b64encode(fontData))
        #     ctx.newline()
        #     ctx.dedent()
        #     ctx.write("}")
        #     ctx.newline()
        #     ctx.endtag("style")
        #     ctx.newline()
        #     ctx.endtag("defs")
        #     ctx.newline()

        return success, error
