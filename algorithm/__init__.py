"""ENS001 - Gemi Rotalama & Envanter Optimizasyonu (düzeltilmiş çözüm).

Bu paket, önceki bozuk Genetik Algoritma implementasyonunun yerine geçen,
HER SERT KISITI sağlayan doğru bir çözüm sunar.

Modüller:
    data      : Excel'den gemi/rota/talep verisini doğru yorumlayarak yükler.
    validator : Bir çözümün tüm kısıtları sağlayıp sağlamadığını bağımsız denetler.
    milp      : PuLP ile kesin (exact) MILP çözücü -> garantili feasible + optimal.
    ga        : Feasibility-korumalı geliştirilmiş Genetik Algoritma (metasezgisel).
"""
