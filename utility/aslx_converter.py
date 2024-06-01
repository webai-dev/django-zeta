#!/usr/bin/env python

"""ASXL to ery converter"""
# pylint: disable=invalid-name,no-member,too-many-locals
import sys
from lxml import etree


def pprint(element):
    """Pretty printer"""
    print(etree.tostring(element, pretty_print=True).decode())


class Converter:
    """Converter"""

    def __init__(self, tree):
        self.tree = tree

    def _get_object_elements(self, element):
        children = []
        for obj in element.xpath("./object"):
            children += self._get_object_elements(obj)

        if element.tag == "object":
            return [element] + children
        return children

    def get_object_elements(self):
        """Recurrsively get all stages"""
        return self._get_object_elements(self.tree.xpath("/asl")[0])

    @staticmethod
    def add_first_era(module_definition, era_name="first"):
        """Add initial era"""
        era_set = etree.SubElement(module_definition, "era_set")
        era = etree.SubElement(era_set, "item")
        etree.SubElement(era, "name").text = era_name
        etree.SubElement(module_definition, "start_era").text = era_name

    def add_block(self, stage_template_block_set, name, xpath, root):
        """Add blocks and translations"""
        stage_template_block = etree.SubElement(stage_template_block_set, "item")
        etree.SubElement(stage_template_block, "name").text = name
        stage_template_block_translation_set = etree.SubElement(stage_template_block, "translations")
        stage_template_block_translation = etree.SubElement(stage_template_block_translation_set, "item")
        etree.SubElement(stage_template_block_translation, "language").text = "en"
        self.append_elements(stage_template_block_translation, "content", xpath, root)

        return stage_template_block

    def append_elements(self, element, tag, xpath, root=None):
        """Return elements for matches"""
        if root is None:
            root = self.tree

        for text in root.xpath(xpath):
            etree.SubElement(element, tag).text = text

    def run(self):
        """Do convertion"""
        # ModuleDefinition
        module_definition = etree.Element("module_definition")
        self.append_elements(module_definition, "name", "/asl/game/@name")
        self.append_elements(module_definition, "comment", "/asl/game/author/text()")
        etree.SubElement(module_definition, "primary_language").text = "en"

        stage_set = etree.SubElement(module_definition, "stage_set")
        inputs = etree.SubElement(module_definition, "inputs")

        self.add_first_era(module_definition)

        for i, obj in enumerate(self.get_object_elements()):
            # Stage
            stage = etree.SubElement(stage_set, "item")
            self.append_elements(stage, "name", "./@name", obj)
            if i == 0:
                # Set start stage
                self.append_elements(module_definition, "start_stage", "./@name", obj)
            stage_template_set = etree.SubElement(stage, "stage_templtes")
            stage_template = etree.SubElement(stage_template_set, "item")
            etree.SubElement(stage_template, "template").text = "default"
            etree.SubElement(stage_template, "theme").text = "default"
            stage_template_block_set = etree.SubElement(stage_template, "blocks")
            # StageTemplateBlock 'content'
            content = self.add_block(stage_template_block_set, "content", "./description/text()", obj)
            if obj.xpath('./picture'):
                # StageTemplateBlock 'picture'
                self.add_block(stage_template_block_set, "picture", "./picture/text()", obj)

            if obj.xpath('./options'):
                # Input
                ery_input = etree.SubElement(inputs, "item")
                self.append_elements(ery_input, "name", "./@name", obj)
                widget_choice_set = etree.SubElement(ery_input, "choices")
                for option_id, option in enumerate(obj.xpath('./options/item')):
                    # InputChoiceItem
                    widget_choice = etree.SubElement(widget_choice_set, "item")
                    widget_choice_translation_set = etree.SubElement(widget_choice, "translations")
                    widget_choice_translation = etree.SubElement(widget_choice_translation_set, "item")
                    self.append_elements(widget_choice, "value", "./key/text()", option)
                    etree.SubElement(widget_choice, "order").text = str(option_id)
                    etree.SubElement(widget_choice_translation, "language").text = "en"
                    self.append_elements(widget_choice_translation, "caption", "./value/text()", option)

                etree.SubElement(content, "ery_input").text = stage.xpath("./name/text()")[0]
        pprint(module_definition)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: {} <input-file-name>".format(sys.argv[0]))
    else:
        Converter(etree.parse(sys.argv[1])).run()
