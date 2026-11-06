import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else { print("usage: visionocr image"); exit(1) }
let url = URL(fileURLWithPath: args[1])
guard let img = NSImage(contentsOf: url), let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff), let cg = rep.cgImage else { print("cannot load"); exit(2) }
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do { try handler.perform([req]) } catch { print("err \(error)"); exit(3) }
for obs in req.results ?? [] { if let c = obs.topCandidates(1).first { print(String(format:"%.3f", c.confidence), c.string) } }
