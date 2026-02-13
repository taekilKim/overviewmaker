"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import { AppSidebar } from "@/components/app-sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs } from "@/components/ui/tabs";

type Menu = "editor" | "assets";
type EditorTab = "input" | "queue";
type AssetTab = "logo" | "artwork";

type Colorway = { file: File; name: string };
type QueueItem = {
  season_item: string;
  season_color: string;
  name: string;
  code: string;
  logo: string;
  artworks: string;
  main_image: File;
  colors: Colorway[];
};

type AssetItem = { name: string; url: string };

const DEFAULT_API = process.env.NEXT_PUBLIC_API_BASE || "https://overviewmaker.onrender.com";

export default function Page() {
  const [menu, setMenu] = useState<Menu>("editor");
  const [editorTab, setEditorTab] = useState<EditorTab>("input");
  const [assetTab, setAssetTab] = useState<AssetTab>("logo");

  const [apiBase, setApiBase] = useState(DEFAULT_API);
  const [seasonItem, setSeasonItem] = useState("JETSET LUXE");
  const [seasonColor, setSeasonColor] = useState("#000000");
  const [name, setName] = useState("MEN'S T-SHIRTS");
  const [code, setCode] = useState("");
  const [logo, setLogo] = useState("선택 없음");
  const [artworks, setArtworks] = useState("");
  const [mainImage, setMainImage] = useState<File | null>(null);
  const [colorFiles, setColorFiles] = useState<Colorway[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);

  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [assetMeta, setAssetMeta] = useState<Record<string, string>>({});
  const [assetUploadFiles, setAssetUploadFiles] = useState<File[]>([]);

  const [status, setStatus] = useState("");
  const [assetStatus, setAssetStatus] = useState("");

  const normalizedApi = useMemo(() => apiBase.replace(/\/$/, ""), [apiBase]);

  async function loadAssets(nextTab = assetTab) {
    try {
      const kind = nextTab === "logo" ? "logo" : "artwork";
      const res = await fetch(`${normalizedApi}/api/assets?kind=${kind}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setAssets(data.files || []);
      setAssetMeta(data.meta || {});
      setAssetStatus("");
    } catch (e: any) {
      setAssetStatus(`자산 조회 실패: ${e.message}`);
    }
  }

  function onColorFilesChange(files: FileList | null) {
    if (!files) return;
    const items = Array.from(files).slice(0, 4).map((file) => ({ file, name: "" }));
    setColorFiles(items);
  }

  async function addQueue() {
    if (!mainImage || !code.trim()) {
      setStatus("품번과 메인 이미지는 필수입니다.");
      return;
    }
    setQueue((prev) => [
      ...prev,
      {
        season_item: seasonItem,
        season_color: seasonColor,
        name,
        code: code.trim(),
        logo,
        artworks,
        main_image: mainImage,
        colors: colorFiles,
      },
    ]);
    setStatus(`'${code.trim()}' 대기열에 추가됨`);
  }

  async function generatePpt() {
    if (queue.length === 0) {
      setStatus("대기열이 비어 있습니다.");
      return;
    }
    const item = queue[0];
    const fd = new FormData();
    fd.append("season_item", item.season_item);
    fd.append("season_color", item.season_color);
    fd.append("name", item.name);
    fd.append("code", item.code);
    fd.append("logo", item.logo);
    fd.append("artworks", item.artworks);
    fd.append("color_names", item.colors.map((c) => c.name).join(","));
    fd.append("main_image", item.main_image);
    item.colors.forEach((c) => fd.append("color_images", c.file));

    try {
      setStatus("생성 중...");
      const res = await fetch(`${normalizedApi}/api/generate`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "BOSS_Golf_SpecSheet.pptx";
      a.click();
      URL.revokeObjectURL(url);
      setStatus("완료: PPT 다운로드를 확인하세요.");
    } catch (e: any) {
      setStatus(`생성 실패: ${e.message}`);
    }
  }

  async function uploadAssets() {
    if (assetUploadFiles.length === 0) {
      setAssetStatus("업로드할 파일을 선택하세요.");
      return;
    }
    try {
      const fd = new FormData();
      fd.append("kind", assetTab === "logo" ? "logo" : "artwork");
      assetUploadFiles.forEach((f) => fd.append("files", f));
      const res = await fetch(`${normalizedApi}/api/assets/upload`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      setAssetUploadFiles([]);
      setAssetStatus("업로드 완료");
      await loadAssets();
    } catch (e: any) {
      setAssetStatus(`업로드 실패: ${e.message}`);
    }
  }

  async function deleteAsset(name: string) {
    try {
      const kind = assetTab === "logo" ? "logo" : "artwork";
      const res = await fetch(`${normalizedApi}/api/assets?kind=${kind}&name=${encodeURIComponent(name)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      await loadAssets();
    } catch (e: any) {
      setAssetStatus(`삭제 실패: ${e.message}`);
    }
  }

  async function updateArtworkMode(name: string, mode: string) {
    try {
      const fd = new FormData();
      fd.append("name", name);
      fd.append("mode", mode);
      const res = await fetch(`${normalizedApi}/api/assets/artwork-mode`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      setAssetMeta((prev) => ({ ...prev, [name]: mode }));
    } catch (e: any) {
      setAssetStatus(`타입 저장 실패: ${e.message}`);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 flex h-14 items-center border-b px-4 md:px-6">
        <div className="flex items-center gap-3">
          <Image src="/bossgolf.svg" alt="BOSS Golf" width={120} height={20} className="h-5 w-auto" priority />
          <h1 className="text-sm font-semibold tracking-tight">
            Overviewer <span className="font-normal text-muted-foreground">for BOSS GOLF</span>
          </h1>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-56px)] w-full">
        <AppSidebar menu={menu} onMenuChange={(m) => { setMenu(m); if (m === "assets") loadAssets(); }} />

        <main className="flex-1 p-4 md:p-6 lg:p-8">
          {menu === "editor" && (
            <>
              <div className="mb-6">
                <h2 className="text-2xl font-bold tracking-tight">슬라이드 제작</h2>
                <p className="mt-1 text-sm text-muted-foreground">제품 정보를 입력하여 스펙 시트를 생성합니다.</p>
              </div>

              <Card>
                <Tabs
                  tabs={[{ key: "input", label: "정보 입력" }, { key: "queue", label: "생성 대기열" }]}
                  value={editorTab}
                  onChange={(v) => setEditorTab(v as EditorTab)}
                />

                {editorTab === "input" && (
                  <CardContent className="space-y-6 p-4 md:p-5">
                    <section>
                      <h3 className="text-base font-semibold">1. 기본 정보</h3>
                      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                        <div>
                          <label className="mb-1.5 block text-xs font-medium text-muted-foreground">시즌 아이템명</label>
                          <Input value={seasonItem} onChange={(e) => setSeasonItem(e.target.value)} />
                        </div>
                        <div>
                          <label className="mb-1.5 block text-xs font-medium text-muted-foreground">시즌 텍스트 색상</label>
                          <Input type="color" value={seasonColor} onChange={(e) => setSeasonColor(e.target.value)} className="h-10" />
                        </div>
                        <div>
                          <label className="mb-1.5 block text-xs font-medium text-muted-foreground">제품명</label>
                          <Input value={name} onChange={(e) => setName(e.target.value)} />
                        </div>
                        <div>
                          <label className="mb-1.5 block text-xs font-medium text-muted-foreground">품번 (필수)</label>
                          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="예: BKFTM1581" />
                        </div>
                      </div>
                    </section>

                    <section className="border-t pt-3">
                      <h3 className="text-base font-semibold">2. 디자인 자산</h3>
                      <div className="mt-3 space-y-3">
                        <div className="rounded-md border border-dashed bg-muted p-3">
                          <label className="mb-1.5 block text-xs font-medium">메인 이미지</label>
                          <Input type="file" onChange={(e) => setMainImage(e.target.files?.[0] || null)} />
                        </div>
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          <div>
                            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">로고 선택</label>
                            <Input value={logo} onChange={(e) => setLogo(e.target.value)} />
                          </div>
                          <div>
                            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">아트워크 선택 (콤마)</label>
                            <Input value={artworks} onChange={(e) => setArtworks(e.target.value)} />
                          </div>
                        </div>
                      </div>
                    </section>

                    <section className="border-t pt-3">
                      <h3 className="text-base font-semibold">3. 컬러웨이 (Colorways)</h3>
                      <div className="mt-3 rounded-md border border-dashed bg-muted p-3">
                        <Input type="file" multiple onChange={(e) => onColorFilesChange(e.target.files)} />
                      </div>
                      <div className="mt-3 space-y-2">
                        {colorFiles.map((c, idx) => (
                          <div key={`${c.file.name}-${idx}`} className="grid grid-cols-[1fr_120px] gap-2">
                            <Input value={c.name} placeholder={`색상명 ${idx + 1}`} onChange={(e) => {
                              const copied = [...colorFiles];
                              copied[idx] = { ...copied[idx], name: e.target.value };
                              setColorFiles(copied);
                            }} />
                            <p className="truncate pt-2 text-xs text-muted-foreground">{c.file.name}</p>
                          </div>
                        ))}
                      </div>
                    </section>

                    <div className="pt-2">
                      <Button onClick={addQueue}>대기열에 추가</Button>
                      <p className="mt-2 text-sm text-muted-foreground">{status}</p>
                    </div>
                  </CardContent>
                )}

                {editorTab === "queue" && (
                  <CardContent className="space-y-4 p-4 md:p-5">
                    <div className="flex items-center justify-between">
                      <h3 className="text-base font-semibold">생성 대기 목록 ({queue.length})</h3>
                      <Button variant="outline" size="sm" onClick={() => setQueue([])}>목록 비우기</Button>
                    </div>
                    <div className="space-y-2">
                      {queue.length === 0 && <div className="rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground">대기 중인 항목이 없습니다.</div>}
                      {queue.map((q, idx) => (
                        <div key={`${q.code}-${idx}`} className="rounded-md border bg-card p-3">
                          <p className="text-sm font-medium">{idx + 1}. {q.code} - {q.name}</p>
                          <p className="mt-1 text-xs text-muted-foreground">컬러: {q.colors.length}개 | 로고: {q.logo} | 아트워크: {q.artworks || "-"}</p>
                        </div>
                      ))}
                    </div>
                    <div className="border-t pt-3">
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">API Base URL</label>
                      <Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} className="max-w-[420px]" />
                      <Button className="mt-3" onClick={generatePpt}>PPT 생성 및 다운로드</Button>
                      <p className="mt-2 text-sm text-muted-foreground">{status}</p>
                    </div>
                  </CardContent>
                )}
              </Card>
            </>
          )}

          {menu === "assets" && (
            <>
              <div className="mb-6">
                <h2 className="text-2xl font-bold tracking-tight">자산 관리</h2>
                <p className="mt-1 text-sm text-muted-foreground">디자인 자산을 업로드하고 관리합니다.</p>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Assets</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />

                  <div className="flex gap-2">
                    <Button variant={assetTab === "logo" ? "default" : "outline"} size="sm" onClick={() => { setAssetTab("logo"); loadAssets("logo"); }}>로고</Button>
                    <Button variant={assetTab === "artwork" ? "default" : "outline"} size="sm" onClick={() => { setAssetTab("artwork"); loadAssets("artwork"); }}>아트워크</Button>
                  </div>

                  {assetTab === "artwork" && (
                    <div className="rounded-md border bg-muted p-3 text-xs text-muted-foreground">
                      - 기본: 높이 20mm (너비 자동)<br />
                      - 가로 타입: 너비 30mm (높이 자동)<br />
                      - 작은 아트워크: 너비 12mm (높이 자동)
                    </div>
                  )}

                  <div className="rounded-md border border-dashed bg-muted p-3">
                    <Input type="file" multiple onChange={(e) => setAssetUploadFiles(Array.from(e.target.files || []))} />
                    <Button className="mt-3" onClick={uploadAssets}>저장하기</Button>
                    <p className="mt-2 text-sm text-muted-foreground">{assetStatus}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    {assets.map((a) => (
                      <div key={a.name} className="rounded-md border p-2">
                        <img src={`${normalizedApi}${a.url}`} alt={a.name} className="h-28 w-full rounded-md border object-contain" />
                        <p className="mt-2 truncate text-xs text-muted-foreground">{a.name}</p>
                        {assetTab === "artwork" && (
                          <div className="mt-2 space-y-1 text-xs">
                            {[
                              ["default", "기본"],
                              ["horizontal", "가로 타입"],
                              ["small", "작은 아트워크"],
                            ].map(([value, label]) => (
                              <label key={value} className="flex items-center gap-1">
                                <input
                                  type="radio"
                                  checked={(assetMeta[a.name] || "default") === value}
                                  onChange={() => updateArtworkMode(a.name, value)}
                                />
                                {label}
                              </label>
                            ))}
                          </div>
                        )}
                        <Button variant="outline" size="sm" className="mt-2" onClick={() => deleteAsset(a.name)}>삭제</Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
