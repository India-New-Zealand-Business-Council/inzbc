import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "C:\\Users\\brett\\Downloads\\Morph-Motion-Template-20-Slides.pptx";
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));

const result = {
  slides: presentation.slides.items.length,
  masters: presentation.masters.items.map((master) => ({
    id: master.id,
    name: master.name,
    elementCount: master.elements?.items?.length ?? master.elements?.length ?? 0,
    placeholders: master.placeholders?.summary?.() ?? null,
  })),
  layouts: presentation.layouts.items.map((layout) => ({
    id: layout.id,
    name: layout.name,
    parentLayoutId: layout.parentLayoutId,
    elementCount: layout.elements?.items?.length ?? layout.elements?.length ?? 0,
    placeholders: layout.placeholders?.summary?.() ?? null,
  })),
  firstSlide: {
    id: presentation.slides.items[0].id,
    layoutId: presentation.slides.items[0].layoutId,
    shapeCount: presentation.slides.items[0].shapes.items.length,
    imageCount: presentation.slides.items[0].images.items.length,
    shapes: presentation.slides.items[0].shapes.items.map((shape) => ({
      id: shape.id,
      name: shape.name,
      hasText: Boolean(shape.text),
      text: shape.text?.toString?.() ?? null,
      keys: Object.keys(shape).sort(),
    })),
    textPrototypeMethods: Object.getOwnPropertyNames(Object.getPrototypeOf(presentation.slides.items[0].shapes.items[4].text)).sort(),
    shapePrototypeMethods: Object.getOwnPropertyNames(Object.getPrototypeOf(presentation.slides.items[0].shapes.items[0])).sort(),
    imagePrototypeMethods: Object.getOwnPropertyNames(Object.getPrototypeOf(presentation.slides.items[0].images.items[0])).sort(),
  },
};

console.log(JSON.stringify(result, null, 2));
