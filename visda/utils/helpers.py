def pick_closest(dets, w, h):
    if not dets: return None
    cx, cy = w/2, h/2
    best, score_best = None, -1
    for (label, conf, (x1,y1,x2,y2)) in dets:
        area = max(0,(x2-x1))*max(0,(y2-y1))
        bx, by = (x1+x2)/2, (y1+y2)/2
        center_bias = 1.0 - min(1.0, (abs(bx-cx)/cx + abs(by-cy)/cy)/2.0) * 0.2
        s = area * center_bias
        if s > score_best:
            score_best, best = s, (label, conf, (x1,y1,x2,y2))
    return best
