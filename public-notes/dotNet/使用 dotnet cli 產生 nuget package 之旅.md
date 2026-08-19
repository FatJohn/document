Using dotnet cli to create NuGet package
===

## 包裝指令
`dotnet pack` 

- 不指定 project or solution 檔案會自動尋找該目錄下的 solution / project 檔案
- 詳細參數請參考文件: [dotnet pack](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-pack)
- project 檔案可以使用 `<IsPackable>` tag 來設定 project 是否是可以被 pack 的，預設值是 **true**
- 下 dotnet pack 後預設執行的流程是先 build 再 pack，如果不要 build 要多加參數 `--no-build` 參數

## Project 檔案要支援包裝成 NuGet 建議所需要得基本 tag
無論是 `SDK-Style` 或 `non SDK-Style` project 都適用，不給這些 tag 一樣能產生 nuget package，但這些參數都會使用預設值帶入，通常不是希望的值，建議都自己補上

建議加入的 tag 如下
* PackageId
* Version
* Authors
* Company
* Description

可以在 project 檔案建立一個獨立的 `<PropertyGroup></PropertyGroup>` 宣告即可，範例如下
``` xml
<PropertyGroup>
  <PackageId>ClassLibDotNetStandard</PackageId>
  <Version>1.0.0</Version>
  <Authors>your_name</Authors>
  <Company>your_company</Company>
  <Description>description</Description>
</PropertyGroup>
```

## 依照需求規劃你要拆分的 NuGet package 方式

若 solution 中僅有單一個 project 可以跳過這邊

下面的說明包裝方式是針對 solution 而非單一 project (註1)

### Solution 的每個 Project 都是各自獨立的 NuGet Package
**所有** project 的 `<IsPackable>` 的值為 **true** 的情況下（就是預設的情況），設定好 ProjectRefence 即可

此時下 dotnet pack 指令產生 nupkg 後，就可以發現在 nupkg 的 nuspec 檔案內容會把ProjectReference 以 `dependency` 形式表示，亦即是相依於另外一個 NuGet Package

並且因為下指令是針對 solution 檔案，所以會把 solution 下所有的 project 都變成 NuGet package 

### Solution 僅想要單一或少數的 NuGet Package
可以僅將需要包裝成 NuGet package 的 project 的 `<IsPackable>` 標示為 **true**，其餘的標示為 **false**

此時 dotnet pack 會將相依的 project 的 assembly 一併打包至 nupkg 的 lib 中

**下方列的比較複雜的測試情境均沒測試過，所以可能會踩到意想不到的雷**
**也許未來某天有空再來驗證看看**

#### 註1
**不建議**在 Solution 有多個 project，並且該 proejct 也有自己的 ProjectReference 的情況下，使用 dotnet pack 去針對 project 下指令產生 NuGet package

此時會發現 `<ProjectReference>` 的 dll 不會正常的包裝進去 nuget 中

根據 [dotnet pack](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-pack) 指令說明中的描述是預期的，目前不支援
```
  If the packed project has references to other projects, the other projects 
  aren't included in the package. Currently, you must have a package per 
  project if you have project-to-project dependencies.
```

若執意要做也是有 workaround 可以參考下面的連結來解決
- [Dotnet pack - include referenced projects](https://josef.codes/dotnet-pack-include-referenced-projects/)
- [Dotnet pack / nuget pack - How to simply pack multiple projects into one package (all projects included in .csproj) & test it?](https://stackoverflow.com/questions/78672095/dotnet-pack-nuget-pack-how-to-simply-pack-multiple-projects-into-one-package)

但還是不建議這樣做，針對 solution 去下指令會單純的多

## 測試 dotnet pack 的各種情境是否正常

### 測試準備
- 建立 4 個 .net standard 2.0 的 SDK-Style 的 project RootLib, Lv1Lib, Lv2Lib, Lv3Lib 並加入同一個 solution
- 每個 Project 都是 `<IsPackable>` 都是為預設值 true
- 設定相依關係
  - RootLib 依賴 Lv1Lib
  - Lv1Lib 依賴 Lv2Lib
  - Lv2Lib 依賴 Lv3Lib

以 Visual Studio 的 Solution Explorer 的角度來看如下
```
- RootLib project
  - ProjectReference
    - Lv1Lib project
      - ProjectRefernece
        - Lv2Lib project
          - ProjectReference
            - Lv3Lib project
              - PackageReference
                - CsvHelper
          - PackageReference
            - NLog
          - Lv2Config (資料夾)
            - Lv2Config.json
      - PackageReference
        - LiteDB
      - Lv1Config (資料夾)
        - Lv1Config.json
  - PackageReference
    - NewtonSoft.Json
  - RootConfig (資料夾)
    - RootConfig.json
```

### 測試驗證方式
- 驗證輸出檔案清單
  - RootLib.nupkg
  - Lv1Lib.nupkg
  - Lv2Lib.nupkg
  - Lv3Lib.nupkg
- 針對 nupkg 解壓縮後看裡面
  - 資料夾結構是否有包含預期的檔案
  - 觀察 nuspec 是否正確

### 測試情境
1. 僅包裝 Root Library ✅
2. 包裝 1 ~ 3 層 Project Reference ✅
3. 僅包裝 Root Library 並有 PackageReference ✅
4. 包裝 1 ~ 3 層 Project Reference 並且每個 Project 有各自的 PackageReference ✅
5. 僅包裝 Root Project 的 Assets 檔案 ✅
6. 包裝 1 ~ 3 層 Project Reference 並且每個 Project 有各自的 Assets 檔案 ✅
7. 僅包裝 Root Project 的 Assets 檔案並要輸出到指定目錄 ✅
8. 包裝 1 ~ 3 層 Project Reference 並且每個 Project 有各自的 Assets 檔案並要輸出到指定目錄 ✅
9. 僅 Root Project 參考外部 assembly (dll) ✅
10. 包裝 1 ~ 3 層 Project Reference 並且各自有參考外部的 assembly (dll) ✅

### 5. 僅包裝 Root Project 的 Assets 補充說明
需要在要包裝的檔案上有手動加上下面 2 個 tag 方能正常
- **Pack (boolean) [可選]** : 表示這個檔案是否需要被包裝，如果檔案標示成 `<None>` 就需要手動加入此 tag 並設定為 true
- **PackageCopyToOutput (boolean)** : 是否要把該檔案放到使用此 NuGet 的 output 資料夾 (例如: bin) 中    

#### 範例
假設 project 在 Config 資料夾下有一個 RootConfig.json 檔案

打開 project 檔案會看到這行
```xml
<None Update="Config\RootConfig.json"/>
```

說明 :
- **None** 對應的是該檔案在 VS 的 **Build Action** 的值是 **None**，以此類推
- 如果沒有看到這行請自行補上，因為 SDK-Style project 會偵測路徑變更，有檔案加入就會自動出現在 Solution Explorer 中但不代表在 project 檔案裡面有 item 紀錄


所以照上方所述，補上支援正確包裝的 tag
```xml
<None Update="Config\RootConfig.json">
  <Pack>true</Pack>
  <PackageCopyToOutput>true</PackageCopyToOutput>
</None>
```

包裝後解壓縮 nupkg 後查看會發現
1. 有 **content** 及 **contentFiles** 2 個資料夾，裡面可以看到對應的檔案
2. 打開 nuspec 檔案就可以看到與單純的僅下 `<Pack>` 為 true 的差異就是多一個 `copyToOutput` 的 attribute

```xml
<files include="any/net8.0/Config/RootConfig.json" buildAction="None"
 copyToOutput="true" />
```

### 6. 包裝 1 ~ 3 層 Project Reference 並且每個 Project 有各自的 Assets 檔案 補充說明
除了同 5 的補充說明要補上該有的 tag 外，需要在每個 `<ProjectReference>` 的地方要補上 `<PrivateAssets>` tag 並且設定為 `analyzers;build` 否則跨層的相依不會正常把檔案帶過去

根據[文件](https://learn.microsoft.com/en-us/nuget/consume-packages/package-references-in-project-files) 的說明，`<PrivateAssets>` 的意思是**反向**列表，所以要能正確的將 PrivateAssets flow 到外層去的話，是需要設定為 `analyzers;build` 的

#### 範例
打開 RootLib project 檔案會看到這行 Lv1Lib 的 ProjectReference
```xml
<ProjectReference Include="..\Lv1Lib\Lv1Lib.csproj"/>
```

接下來補上 `<PrivateAssets>` 的 tag
``` xml
<ProjectReference Include="..\Lv1Lib\Lv1Lib.csproj">
  <PrivateAssets>analyzers;build</PrivateAssets>
</ProjectReference>
```

最終解壓縮 nupkg 後查看會發現在 `include` 的 attribute 的值比不加上 `<PrivateAssets>` 的差異
- 不加的話是 `Build,Analyzers` 
- 加上的話是 `Runtime,Compile,Native,ContentFiles,BuildTransitive`

下面是加上後 nupkg 檔案中的 nuspec 結果
``` xml
<group targetFramework=".NETStandard2.0">
  <dependency id="Lv1Lib" version="1.0.0" include="Runtime,Compile,Native,ContentFiles,BuildTransitive" />
</group>
```

### 7. 僅包裝 Root Project 的 Assets 檔案並要輸出到指定目錄 補充說明
需要搭配 `.targets` 檔案才可做到，透過 `.targets` 檔案裡面執行的 msbuild 動作來把檔案複製到想要的地方

#### 步驟如下
1. 建立一個與 {PackageId}.targets 檔案
   - PackageId 就是看 Project 檔案裡面的設定
   - 需要與 PackageId 同名否則不會被執行
2. 在 {PackageId}.targets 檔案編輯想要做的複製檔案的行為
3. 將 {PackageId}.targets 檔案包裝到 nuget 的 `build` 資料夾
    - 必須要是 `build` 否則 {PackageId}.targets 檔案不會被不會被執行
4. 移除 Assets 檔案的 `<PackageCopyToOutput>`
    - 使用 {PakcageId}.targets 來作複製，就不需要內建的機制了，不然會重複出現檔案或被蓋掉等不預期的行為

#### .targets 檔案範例
僅供參考，可以依照需求作調整


##### 範例 1

複製 NuGet content 中的所有檔案到目標資料夾
``` xml
<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <!-- Define properties for source and destination paths -->
  <PropertyGroup>
    <!-- Source directory relative to the NuGet package root -->
    <MyContentSourceDir>$(MSBuildThisFileDirectory)\..\content</MyContentSourceDir>   
    <!-- Default destination directory - can be overridden by package consumers -->
    <MyContentDestDir Condition="'$(MyContentDestDir)' == ''">$(ProjectDir)\ExternalContent</MyContentDestDir>
  </PropertyGroup>
  <!-- Define item group for content files -->
  <ItemGroup>
    <!-- Include all files from the content directory -->
    <MyContentFiles Include="$(MyContentSourceDir)\**\*.*" />
  </ItemGroup>
  <!-- Target to copy files before build -->
  <Target Name="CopyMyContent" BeforeTargets="Build">
    <!-- Create destination directory if it doesn't exist -->
    <MakeDir Directories="$(MyContentDestDir)" />
    <!-- Copy the files -->
    <Copy
      SourceFiles="@(MyContentFiles)"
      DestinationFiles="@(MyContentFiles->'$(MyContentDestDir)\%(RecursiveDir)%(Filename)%(Extension)')"
      SkipUnchangedFiles="true">
      <Output TaskParameter="CopiedFiles" ItemName="MySuccessfullyCopiedFiles" />
    </Copy>
  </Target>
</Project>
```

##### 範例 2

此範例是把 NuGet content 中 RootConfig 資料夾下所有的 json 檔案複製到 project 的 Assets 目錄中，再從 Assets 目錄複製到 Output 目錄，  
展示如果在自己使用的 Project 檔案中有調整設定，不會被 nuget 裡面的覆蓋掉

``` xml
<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <ConfigSourceFolderRoot>$(MSBuildThisFileDirectory)..\content\RootConfig</ConfigSourceFolderRoot>
    <ConfigDestinationFolderRoot>$(MSBuildProjectDirectory)\Assets</ConfigDestinationFolderRoot>
    <ConfigOutputFolderRoot>$(OutDir)Config</ConfigOutputFolderRoot>
  </PropertyGroup>

  <ItemGroup>
    <ConfigSourceFilesRoot Include="$(ConfigSourceFolderRoot)\**\*.json" />
  </ItemGroup>

  <!-- Copy the config file if it doesn't exist in the project -->
  <Target Name="RootCopyMyLibraryConfig" BeforeTargets="Build">
    <Message Text="Copying Config files from: $(ConfigSourceFolderRoot) to: $(ConfigDestinationFolderRoot)" Importance="high" />
    
    <Copy
      SourceFiles="@(ConfigSourceFilesRoot)"
      DestinationFiles="@(ConfigSourceFilesRoot->'$(ConfigDestinationFolderRoot)\%(RecursiveDir)%(Filename)%(Extension)')"
      SkipUnchangedFiles="true" />

    <!--Declare here after above task. Because only then can get correct file lists-->
    <ItemGroup>
      <ConfigDestinationFilesRoot Include="$(ConfigDestinationFolderRoot)\**\*.json" />
    </ItemGroup>

    <Message Text="Copying Config files from: $(ConfigDestinationFolderRoot) to: $(ConfigOutputFolderRoot)" Importance="high" />
    
    <Copy
      SourceFiles="@(ConfigDestinationFilesRoot)"
      DestinationFiles="@(ConfigDestinationFilesRoot->'$(ConfigOutputFolderRoot)\%(RecursiveDir)%(Filename)%(Extension)')"
      SkipUnchangedFiles="true">
      <Output TaskParameter="CopiedFiles" ItemName="CopiedConfigFilesRoot" />
    </Copy>

    <Message Text="Copied Config files: @(CopiedConfigFilesRoot -> '%(Filename)%(Extension)')" Importance="normal" />
  </Target>

</Project>
```

說明：
- `<PropertyGroup>` 及 `<ItemGroup>` 裡面的 **變數名稱** 可以自己更動
  - 為什麼要另外把檔案清單額外寫在 `<ItemGroup>` 裡面呢？因為裡面有特殊字元，如果寫在 `<PropertyGroup>` 中會造成 .targets 檔案執行錯誤
- 可以看到 `ConfigDestinationFilesRoot` 這個 ItemGroup 宣告的變數是放在後面而不是直接放在最上方，原因是時機點，targets 檔案是一行一行執行的，所以如果放在上方執行到的時候 `$(ConfigDestinationFolderRoot)\**\*.json` 並不會取得任何的值，因為此時第一個 `<Copy>` 還沒執行

#### 將 .targets 檔案包裝到 nuget 的 `build` 資料夾
打開 project 檔案新增

``` xml
<ItemGroup>
  <None Update="RootLib.targets" Pack="true" PackagePath="build" />
</ItemGroup>
```

### 8. 使包裝 1 ~ 3 層 Project Reference 並且每個 Project 有各自的 Assets 檔案並要輸出到指定目錄 補充說明

需要做此處理的每個 Project 都要做，同 7 中說的步驟的事項，僅步驟 3 需要微調，除了放置到 `build` 外要新增一個到 `buildTransitive`

需要注意每個 .targets 檔案中的 `<PropertyGroup>` 及 `<ItemGroup>` 定義的名稱在不同的檔案中不能重複，否則在 msbuild 執行的過程中永遠拿到同一個值

放到 `buildTransitive` 的目的是讓該資料夾的東西可以**穿透**多層 nuget 相依到使用的 Proejct 去

範例
``` xml
<ItemGroup>
  <None Update="RootLib.targets" Pack="true" PackagePath="build;buildTransitive" />
</ItemGroup>
```

#### Reference
- [Controlling dependency assets](https://learn.microsoft.com/en-us/nuget/consume-packages/package-references-in-project-files#controlling-dependency-assets)
  - 官方文件，是 NuGet 5.0 之後才支援的
    - 根據 [NuGet 5.0 release note](https://learn.microsoft.com/en-us/nuget/release-notes/nuget-5.0-rtm) 是跟著 VS 2019 出的
- [Roslyn 打包 NuGet 包 BuildTransitive 文件夹用于穿透依赖传递拷贝文件](https://blog.lindexi.com/post/Roslyn-%E6%89%93%E5%8C%85-NuGet-%E5%8C%85-BuildTransitive-%E6%96%87%E4%BB%B6%E5%A4%B9%E7%94%A8%E4%BA%8E%E7%A9%BF%E9%80%8F%E4%BE%9D%E8%B5%96%E4%BC%A0%E9%80%92%E6%8B%B7%E8%B4%9D%E6%96%87%E4%BB%B6.html)
- [Allow package authors to define build assets transitive behavior](https://github.com/NuGet/Home/wiki/Allow-package--authors-to-define-build-assets-transitive-behavior)


### 9. 僅 Root Project 參考外部 assembly (dll) 補充說明
步驟
1. 加入外部 assembly (dll) 的 Reference
2. 把外部 assembly (dll) 在 project 檔案加入一個 entry 讓他可以包裝到 nuget 的 lib 資料夾中

#### 1. 加入外部 assembly (dll) 的 Reference

在 SDK-Style Project 如果無法用 Visual Studio 加入 dll reference 的話，可以直接用手動的方式在 project 檔案加入

> TargetFramework 是 .NET Framework 的時候，才可以透過 Visual Studio 的 add reference 加入外部參考，其他的需要手動

``` xml
<ItemGroup>
  <Reference Include="MyAssembly">
    <HintPath>path\to\MyAssembly.dll</HintPath>
  </Reference>
</ItemGroup>
```

#### 2 : 把外部 assembly (dll) 在 project 檔案加入一個 entry 讓他可以包裝到 nuget 的 lib 資料夾中

在 Project 檔案加入一個 `<None>` 讓 dotnet pack 認得這個是需要被包裝進去的檔案

範例:

assembly 在 project 檔案目錄或其子目錄下的範例
``` xml
<None Update="path\to\MyAssembly.dll" Pack="true" PackagePath="lib\$(TargetFramework)" />
```

assembly 與 project 不同目錄下的範例，多了一個 Link，必須要把檔案視為 project 的一部分才可以正確的包裝
``` xml
<None Update="path\to\MyAssembly.dll" Link="MyAssembly.dll" Pack="true" PackagePath="lib\$(TargetFramework)" />
```

兩個範例差異在那個 `Link` attribute，這樣做就是把這個檔案當作 project 的一部分 

**注意 : `PackagePath` 不要任意更動，否則可能不會自動複製到 output 目錄中**

### 10. 包裝 1 ~ 3 層 Project Reference 並且各自有參考外部的 assembly (dll) 補充說明
要在每個 Project 都做一樣的設定外，要記得同 6 的補充說明在 ProjectReference 的地方要補上 `<PrivateAssets>analyzers;build</PrivateAssets>`

## 測試後補充
測試情境 5, 6 因為是一定會輸出到 Ouput，所以在 output 資料夾中的檔案一律會被 nuget 裡面的內容覆蓋

## Metapackage
簡單來說因為你會把很多相依的 project 做成 NuGet，而 Metapackage 就是僅有 package 相依性沒有任何自己 binary 的 NuGet package

目的我認為是
- 更好的 DX (Developer Experience)，因為可以裝一個 NuGet Package 而不用裝千千萬萬個 NuGet
- 更好的相依版本控管，因為裝特定版本的 Metapackage 就是對應到特定版本的 NuGet packages，不會需要自己安裝每個相依的然後不小心裝錯版本

可以參考下面的方式來製作及說明
- [How to create a NuGet metapackage](https://danielwertheim.se/how-to-create-a-nuget-metapackage/)
  - metapackage : `a package without any contents, one that just references other packages`
- [.NET project SDKs](https://learn.microsoft.com/en-us/dotnet/core/project-sdk/overview)
  - `A metapackage is a framework-based package that consists only of dependencies on other packages. Metapackages are implicitly referenced based on the target frameworks specified in the TargetFramework or TargetFrameworks (plural) property of your project file.`

## non SDK-Style project 也可以使用像 dotnet pack 指令來包裝嗎？答案是可以
    
可以使用 msbuild 來達到指令是 `msbuild -t:pack` 

根據 [Create a NuGet package using MSBuild](https://learn.microsoft.com/en-us/nuget/create-packages/creating-a-package-msbuild) 所述，dotnte pack 及 msbuild -t:pack 功用是相同的
```
The command that creates a package, msbuild -t:pack, is functionally 
equivalent to dotnet pack.
```

另外根據 [Create a NuGet package using MSBuild](https://learn.microsoft.com/en-us/nuget/create-packages/creating-a-package-msbuild) 說明，non SDK-Style 要支援還要注意兩件事情
1. 需要使用 `<PackageReference>` （不能用 packages.config 的方式）
2. 需要把 `NuGet.Build.Tasks.Pack` NuGet 加入到每個 project 中

## 其他產生 NuGet package 替代方式

下面針對的都是一樣都是減少手動編輯 nuspec 的方式，畢竟我們想要減少人工的失誤

### 1. 用 NuGet CLI ([nuget spec](https://learn.microsoft.com/en-us/nuget/reference/cli-reference/cli-ref-spec))
- 優點
    - 原生（？）
    - 無其他相依性
- 缺點
    - 僅能產生基本的 nuspec 不會依照 PackageReference 和 ProjectReference 產生對應的 attribute

### 2. 使用 [nugetizer](https://github.com/devlooped/nugetizer)
- 優點
  - 使用原生地 SDK-Style project 檔案，並且使用 msbuild native 原生的 tag
  - 無須將 ProjectReference 都要產生為各自的 nuget package (此種原生行為也支援) 也能正確的產生對應的 nuspec 檔案，包含相依或相依的相依
    - 將不需要產生 nuget package Project 的 `<IsPackable>` 設定為 false，這樣會正確地將所有相依的關係建立成正確的 nuspec
    - 雖然原生的 dotnet pack 將相依的 
- 缺點
  - 僅支援 SDK-Style project
  - 每個 Project 均需要去使用 **NuGetizer** 這個 NuGet

舉例
```
- RootLib (IsPackable = true)
  - ProjectReference
    - Lv1Lib (IsPackable = false)
      - ProjectRefernece
        - Lv2Lib (IsPackable = true)
          - ProjectReference
            - Lv3Lib (IsPackable = true)
              - PackageReference
                - CsvHelper
          - PackageReference
            - NLog
      - PackageReference
        - LiteDB
      - Lv1Config (資料夾)
        - Lv1Config.json
  - PackageReference
    - NewtonSoft.Json
  - RootConfig (資料夾)
    - RootConfig.json
```

透過 NuGetizer 產生的 nuspec
```xml
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2012/06/nuspec.xsd">
  <metadata>
    <id>RootLib</id>
    <version>1.0.0</version>
    <authors>ASML</authors>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <description>Description for Root</description>
    <repository type="git" commit="2bdb8493e76a5eb546d015ecc002debb8b6aa6ce" />
    <dependencies>
      <group targetFramework="net8.0">
        <dependency id="Newtonsoft.Json" version="13.0.3" />
        <dependency id="LiteDB" version="5.0.17" />
        <dependency id="Lv2Lib" version="1.0.0" />
        <dependency id="Lv3Lib" version="1.0.0" />
      </group>
    </dependencies>
  </metadata>
  <files>
    <file src="D:\@P\CB9\NuGetPackCLITest\RootLib\bin\Debug\net8.0\Config\RootConfig.json" target="lib\net8.0\Config\RootConfig.json" />
    <file src="D:\@P\CB9\NuGetPackCLITest\RootLib\bin\Debug\net8.0\RootLib.dll" target="lib\net8.0\RootLib.dll" />
    <file src="D:\@P\CB9\NuGetPackCLITest\RootLib\bin\Debug\net8.0\RootLib.pdb" target="lib\net8.0\RootLib.pdb" />
    <file src="D:\@P\CB9\NuGetPackCLITest\Lv1Lib\bin\Debug\net8.0\Lv1Config\Lv1Config.json" target="lib\net8.0\Lv1Config\Lv1Config.json" />
    <file src="D:\@P\CB9\NuGetPackCLITest\Lv1Lib\bin\Debug\net8.0\Lv1Lib.dll" target="lib\net8.0\Lv1Lib.dll" />
    <file src="D:\@P\CB9\NuGetPackCLITest\Lv1Lib\bin\Debug\net8.0\Lv1Lib.pdb" target="lib\net8.0\Lv1Lib.pdb" />
  </files>
</package>
```

同樣的結構用 dotnet pack 包裝的 nupkg 解壓縮出來的 nuspec
```xml
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>RootLib</id>
    <version>1.0.0</version>
    <authors>ASML</authors>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <description>Description for Root</description>
    <repository type="git" commit="2bdb8493e76a5eb546d015ecc002debb8b6aa6ce" />
    <dependencies>
      <group targetFramework="net8.0">
        <dependency id="Newtonsoft.Json" version="13.0.3" />
        <dependency id="LiteDB" version="5.0.17" />
      </group>
    </dependencies>
  </metadata>
</package>
```

解壓縮 nupkg 後的 lib 資料夾有正確的將 RootLib.dll, Lv1Lib.dll 都包裝進去，但那 2 個 json 檔案卻也被包進了 lib 資料夾中，並且可以看到 nuspec 並沒有對應輸出檔案的 tag，就會導致使用的人不會正確的出現這 2 個 json 檔案

## 關於 dotnet cli 和 msbuild
- 每個版本的 .NET (.net core 3.1 之後) 都包含有自己的 msbuild (以 dll 形式存在)
- 功能與 msbuild 相同
- dotnet cli 裡面也有 [dotnet msbuild](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-msbuild) 的命令
  - `The dotnet msbuild command allows access to a fully functional MSBuild.The command has the exact same capabilities as the existing MSBuild command-line client for SDK-style projects only.`
- dotnet 環境與 msbuild 等等對應版本關係可以參考:[.NET SDK, MSBuild, and Visual Studio versioning](https://learn.microsoft.com/en-us/dotnet/core/porting/versioning-sdk-msbuild-vs)

## Reference
- [Package creation workflow](https://learn.microsoft.com/en-us/nuget/create-packages/overview-and-workflow)
- [Identify the project format](https://learn.microsoft.com/en-us/nuget/resources/check-project-format)  
- [dotnet build](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-build)
  - `dotnet build uses MSBuild to build the project, so it supports both parallel and incremental builds. For more information, see Incremental Builds.`
- [Adding nuget pack as a msbuild target](https://github.com/NuGet/Home/wiki/Adding-nuget-pack-as-a-msbuild-target)
- [MSBuild .props and .targets in a package](https://learn.microsoft.com/en-us/nuget/concepts/msbuild-props-and-targets)
- [Customize your build](https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-your-build?view=vs-2022)
  - 裡面有介紹 `.props` 和 `.targets` 的差異
    - `.props` files are imported early in the import order.
    - `.targets` files are imported late in the build order.
