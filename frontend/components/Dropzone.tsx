/**
 * Componente de carga: soporta carga individual (un archivo) y carga masiva
 * por carpeta completa (webkitdirectory), cumpliendo el requerimiento del
 * Módulo de Carga de Archivos.
 */
"use client";

import { useCallback, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FolderUp } from "lucide-react";

interface DropzoneProps {
  mode: "single" | "folder";
  onFilesSelected: (files: File[]) => void;
}

// Mismas extensiones que acepta el backend (ver ALLOWED_IMAGE_EXTENSIONS en
// storage_service.py). El selector nativo de carpeta (webkitdirectory) no
// filtra nada: incluye archivos de sistema ocultos que el navegador nunca
// muestra en carga individual (ej. .DS_Store, que macOS crea en TODAS las
// carpetas) o carpetas de metadata. Antes, uno de esos archivos bastaba para
// que el backend rechazara el lote COMPLETO ("Formato no soportado, sin
// extensión") sin subir ni una sola foto real.
const ALLOWED_IMAGE_EXTENSIONS = new Set([
  ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic",
  ".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2",
]);

function isRealPhotoFile(file: File): boolean {
  const name = file.name;
  if (name.startsWith(".")) return false; // .DS_Store, ._archivo (AppleDouble), etc.
  const dot = name.lastIndexOf(".");
  if (dot === -1) return false;
  return ALLOWED_IMAGE_EXTENSIONS.has(name.slice(dot).toLowerCase());
}

export default function Dropzone({ mode, onFilesSelected }: DropzoneProps) {
  const [fileCount, setFileCount] = useState(0);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      setFileCount(accepted.length);
      onFilesSelected(accepted);
    },
    [onFilesSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: mode === "folder",
    accept: {
      "image/*": [".jpg", ".jpeg", ".png", ".tiff", ".heic"],
      "application/octet-stream": [".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"],
    },
  });

  function handleFolderInput(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []).filter(isRealPhotoFile);
    setFileCount(files.length);
    onFilesSelected(files);
  }

  if (mode === "folder") {
    return (
      <div
        onClick={() => folderInputRef.current?.click()}
        className="border-2 border-dashed border-photonix-border rounded-xl2 p-10 text-center cursor-pointer hover:border-photonix-accent transition-colors"
      >
        <FolderUp className="mx-auto mb-3 text-photonix-steel" size={36} />
        <p className="font-medium">Selecciona una carpeta completa</p>
        <p className="text-sm text-photonix-textMuted mt-1">
          Se cargarán todas las fotos compatibles (RAW, JPEG, PNG, TIFF, HEIC, DNG y más).
        </p>
        {fileCount > 0 && (
          <p className="text-sm text-photonix-accent mt-3">{fileCount} archivos seleccionados</p>
        )}
        <input
          ref={folderInputRef}
          type="file"
          // @ts-expect-error: atributo no estándar pero soportado por navegadores modernos
          webkitdirectory=""
          directory=""
          multiple
          className="hidden"
          onChange={handleFolderInput}
        />
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl2 p-10 text-center cursor-pointer transition-colors ${
        isDragActive ? "border-photonix-accent" : "border-photonix-border hover:border-photonix-accent"
      }`}
    >
      <input {...getInputProps()} />
      <UploadCloud className="mx-auto mb-3 text-photonix-steel" size={36} />
      <p className="font-medium">Arrastra una foto aquí o haz clic para elegir</p>
      <p className="text-sm text-photonix-textMuted mt-1">JPG, PNG, TIFF, HEIC o RAW</p>
      {fileCount > 0 && (
        <p className="text-sm text-photonix-accent mt-3">{fileCount} archivo seleccionado</p>
      )}
    </div>
  );
}
