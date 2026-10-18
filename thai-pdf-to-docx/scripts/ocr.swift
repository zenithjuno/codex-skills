// macOS Vision OCR for scan / broken-text-layer pages.  Built on first use by ocr.py (swiftc), binary cached outside the repo.
//   ocr <image.png> [--chars]
// default : one line per recognised text line:  "x y<TAB>text"      (x,y = top-left, 0..1 of the image, y downward)
// --chars : one line per character:             "x0 y0 x1 y1<TAB>char"
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count >= 2, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("cannot read image\n".data(using: .utf8)!)
    exit(1)
}
let perChar = args.contains("--chars")
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false          // correction "fixes" Thai into other words
req.recognitionLanguages = ["th-TH", "en-US"]
if #available(macOS 13.0, *) { req.revision = VNRecognizeTextRequestRevision3 }
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
for o in (req.results ?? []) {
    guard let c = o.topCandidates(1).first else { continue }
    if perChar {
        let s = c.string
        var i = s.startIndex
        while i < s.endIndex {
            let j = s.index(after: i)
            if let b = try? c.boundingBox(for: i..<j)?.boundingBox {
                print(String(format: "%.4f %.4f %.4f %.4f\t", b.minX, 1 - b.maxY, b.maxX, 1 - b.minY) + String(s[i]))
            }
            i = j
        }
    } else {
        let b = o.boundingBox
        print(String(format: "%.3f %.3f\t", b.minX, 1 - b.maxY) + c.string)
    }
}
