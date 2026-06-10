# Proposal slides

Slide images shown in the assistant's side panel when a proposal question is
answered. Served at `GET /slides/{image}.jpg`; the `{image}` stems are referenced
from `app/proposal/flows.py`.

Naming convention (stem = `{deck}-{page}`):

- `orals-6.jpg`, `orals-7.jpg`, `orals-21.jpg` … — pages of
  *Schaeffler Medias Ask Me Anything_ORALS.pdf*
- `rfq-5.jpg` — page of *Schaeffler_Medias_Ask_Me_Anything_RFQ_Response.pdf*

These are rendered from the source decks with PyMuPDF, e.g.:

```python
import fitz
doc = fitz.open("…/ORALS.pdf")
doc[5].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save("slides/orals-6.jpg")
```

If an image is missing the frontend `SlideDeck` widget renders a labelled
placeholder, so the Q&A still works without the exports present.
"""
