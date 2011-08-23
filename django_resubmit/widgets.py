# coding: utf-8
from __future__ import absolute_import

import functools
from django.forms.widgets import CheckboxInput, ClearableFileInput, HiddenInput, Input
from django.forms.widgets import FILE_INPUT_CONTRADICTION
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from  xml.etree import cElementTree as ET

from .conf import settings
from .storage import get_default_storage
from .thumbnailer import ThumbnailManager


FILE_INPUT_CLEAR = False


class FileWidget(ClearableFileInput):

    class Media:
        css = {'all': (settings.STATIC_URL + 'django_resubmit/widget.css',)}
        js = (#'https://raw.github.com/malsup/form/master/jquery.form.js',
              settings.STATIC_URL + 'django_resubmit/jquery.form.js',
              settings.STATIC_URL + 'django_resubmit/widget.js',)

    def __init__(self, *args, **kwargs):
        self.thumb_size = settings.RESUBMIT_THUMBNAIL_SIZE
        self.set_storage(get_default_storage())
        self.hidden_key = u""
        self.isSaved = False
        super(FileWidget, self).__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        self.hidden_key = data.get(self._hidden_keyname(name), "")

        upload = super(FileWidget, self).value_from_datadict(data, files, name)

        # user checks 'clear' or checks 'clear' and uploads a file
        if upload is FILE_INPUT_CLEAR or upload is FILE_INPUT_CONTRADICTION:
            if self.hidden_key:
                self._storage.clear_file(self.hidden_key)
                self.hidden_key = u""
            return upload

        if files and name in files:
            if self.hidden_key:
                self._storage.clear_file(self.hidden_key)
            upload = files[name]
            self.hidden_key = self._storage.put_file(upload)
        elif self.hidden_key:
            restored = self._storage.get_file(self.hidden_key, name)
            if restored:
                upload = restored
                files[name] = upload
            else:
                self.hidden_key = u""

        return upload

    def render(self, name, value, attrs=None):
        default_attrs = {'class':'resubmit'}
        attrs = attrs or {}
        attrs.update(default_attrs)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)
        
        thumbnail = self._thumbnail(self.thumb_size, value)
        if thumbnail:
            width, height = thumbnail.size
            thumbnail_url = thumbnail.url
        else:
            width, height = self.thumb_size
            thumbnail_url = None

        data = {'name': name,
                'value': value,
                'input': Input().render(name, None, self.build_attrs(attrs, type=self.input_type)),
                'input_text': self.input_text,
                'input_has_initial': value and (hasattr(value, "url") or self.hidden_key),
                'initial_text': self.initial_text,
                'initial_name': force_unicode(value.name) if value else None,
                'initial_url': value.url if hasattr(value, 'url') else None,
                'is_required': self.is_required,
                'key_input': HiddenInput().render(self._hidden_keyname(name), self.hidden_key or '', {}),
                'thumbnail_url': thumbnail_url,
                'clear_checkbox': CheckboxInput().render(checkbox_name, False, attrs={'id': checkbox_id}),
                'clear_checkbox_id': checkbox_id,
                'clear_checkbox_name': checkbox_name,
                'clear_checkbox_label': self.clear_checkbox_label,
                'preview_width': width,
                'preview_height': height,
        }

        return mark_safe(force_unicode(ET.tostring(self._html(data))))

    def _html(self, data):
        t = HtmlBuilder()
        s = StyleBuilder()

        return t.div({'class': 'resubmit-widget'},
                    t.div({
                        'class': 'resubmit-preview',
                        'style': s({
                            'width': s.px(data['preview_width']),
                            'height': s.px(data['preview_height']),
                            'display': 'none' if not data['thumbnail_url'] else None})},
                        t.img({
                            'class': 'resubmit-preview__image',
                            'style': s({
                                'max-width': s.px(data['preview_width']),
                                'max-height': s.px(data['preview_height']),
                                }),
                            #'alt': 'preview',
                            'src': data['thumbnail_url'] or None})),
                    t.a({
                        'class': 'resubmit-initial',
                        'style': s({
                            'display': 'none' if not data['input_has_initial'] else None}),
                        'href': data['initial_url'],
                        'target': '_blank'},
                        data['initial_name'] or u' '),
                    t.html(data['input'], {
                        'class': 'resubmit-input'}),
                    t.div({
                        'class': 'resubmit-clear',
                        'style': s({
                            'display': 'none' if not data['input_has_initial'] else None})},
                        t.html(data['clear_checkbox'], {
                            'class': 'resubmit-clear__checkbox'}),
                        t.label({
                            'for': data['clear_checkbox_id'],
                            'class': 'resubmit-clear__label',},
                            data['clear_checkbox_label'])) if not data['is_required'] else None,
                    t.html(data['key_input']),
                   )

    def _hidden_keyname(self, name):
        return "%s-cachekey" % name

    def _thumbnail(self, size, value):
        """ Make thumbnail and return url"""
        if self.hidden_key:
            path = self.hidden_key
        elif hasattr(value, 'url'):
            path = value.name
        else:
            return None
        try:
            thumbnail_manager = ThumbnailManager()
            return thumbnail_manager.thumbnail(size, path)
        except Exception:
            return None

    def set_storage(self, value):
        self._storage = value


################################################################################
# Html builder

def filter_attributes(value):
    return dict(filter(lambda kv: False if kv[1] is None or kv in set([('style', ''), ('class', '')]) else True, value.items()))


class StyleBuilder(object):

    def __call__(self, data):
        return u"; ".join(u"%s:%s" % kv for kv in filter_attributes(data).items())

    def px(self, value):
        return u"%dpx" % value


class HtmlBuilder(object):

    def __call__(self, tag, *args):
        if tag == 'html':
            elem = ET.fromstring(args[0])
            args = args[1:]
        elif tag == 'text':
            return u"".join(args)
        else:
            elem = ET.Element(tag)
        for item in args:
            if item is None:
                continue
            if isinstance(item, dict):
                if 'class' in item and 'class' in elem.attrib:
                    class_set = elem.attrib['class'].split()
                    for cls in item['class'].split():
                        if cls not in class_set:
                            class_set += [cls]
                    item['class'] = u' '.join(class_set)
                elem.attrib.update(filter_attributes(item))
            elif ET.iselement(item):
                elem.append(item)
            else:
                if len(elem):
                    elem[-1].tail = (elem[-1].tail or u"") + unicode(item)
                else:
                    elem.text = (elem.text or u"") + unicode(item)
        return elem

    def __getattr__(self, tag):
        return functools.partial(self, tag)

