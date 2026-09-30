import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/Ramchander Dabral/Downloads/SIH2026-IDEA-Presentation-Format.pptx'));
console.log('slides collection',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides)));
console.log('slide',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.getItem(6))));
console.log('shape',Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides.getItem(1).shapes.items[0])));
console.log(p.help('delete slide',{include:['index','examples','notes'],maxChars:5000}));
