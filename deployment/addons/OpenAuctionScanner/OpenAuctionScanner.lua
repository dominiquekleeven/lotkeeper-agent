OpenAuctionScanner = OpenAuctionScanner or {}
local OAS = OpenAuctionScanner

-- ============================================================================
-- CONSTANTS AND CONFIGURATION
-- ============================================================================
local VERSION = "1.0.1"

OAAData = OAAData or {}

-- Temporary storage during scanning
local TEMP_OAAData = {}

-- Create a persistent frame for OnUpdate checks to avoid frame creation overhead
local checkFrame = CreateFrame("Frame")

-- Cache for GetItemInfo calls to avoid repeated slow API calls
local itemInfoCache = {}

-- Localize frequently called functions for performance
local GetAuctionItemClasses = GetAuctionItemClasses
local GetAuctionItemInfo = GetAuctionItemInfo
local GetAuctionItemLink = GetAuctionItemLink
local GetItemInfo = GetItemInfo
local GetRealmName = GetRealmName
local GetNumAuctionItems = GetNumAuctionItems
local CanSendAuctionQuery = CanSendAuctionQuery
local QueryAuctionItems = QueryAuctionItems
local CreateFrame = CreateFrame
local UIParent = UIParent
local table_insert = table.insert
local string_lower = string.lower
local string_find = string.find
local string_match = string.match
local math_ceil = math.ceil
local tonumber = tonumber
local ipairs = ipairs
local pairs = pairs

-- Print with green prefix
local oas_print = function(msg)
    print("|cFF00FF00[OAS]|r " .. msg)
end

-- Print with blue prefix
local oas_print_info = function(msg)
    print("|cFF0080FF[OAS]|r " .. msg)
end

-- Create the main frame for event handling
local oasFrame = CreateFrame("Frame", "OpenAuctionScannerFrame")

-- Item class names
local TARGET_CLASS_NAMES = {
    "weapon",
    "armor",
    "container",
    "consumable",
    "glyph",
    "trade goods",
    "projectile",
    "quiver",
    "recipe",
    "gem",
    "miscellaneous",
    "quest",
}

local MAX_ITEMS_PER_PAGE = 50

-- ============================================================================
-- GLOBAL STATE
-- ============================================================================
local state = {
    currentClassName = nil,
    currentClassNameIndex = 1,
    currentPage = 0,
    totalPages = 0,
    totalItems = 0,
    processedItems = 0,
    isProcessing = false,
    isDone = false,
    isDataCommitted = false,
}

local function ResetState()
    state = {
        currentClassName = nil,
        currentClassNameIndex = 1,
        currentPage = 0,
        totalPages = 0,
        totalItems = 0,
        processedItems = 0,
        isProcessing = false,
        isDone = false,
        isDataCommitted = false,
    }
end

-- Get cached item info to avoid repeated GetItemInfo calls
local function GetCachedItemInfo(itemId)
    if not itemId then return nil, nil end
    
    if itemInfoCache[itemId] then
        return itemInfoCache[itemId].maxStack, itemInfoCache[itemId].vendorPrice
    end
    
    local _, _, _, _, _, _, _, maxStackSize, _, _, vendorPriceValue = GetItemInfo(itemId)
    local maxStack = maxStackSize or 1
    local vendorPrice = vendorPriceValue or 0
    
    -- Cache the results
    itemInfoCache[itemId] = {
        maxStack = maxStack,
        vendorPrice = vendorPrice
    }
    
    return maxStack, vendorPrice
end

-- Clear the item info cache
local function ClearItemInfoCache()
    itemInfoCache = {}
end



-- ============================================================================
-- UI
-- ============================================================================
-- Create the status display frame
-- Initialize the addon
function OAS:Initialize()
    -- Create main frame with clean styling (taller and narrower)
    self.statusFrame = CreateFrame("Frame", "OpenAuctionScannerStatusFrame", UIParent)
    self.statusFrame:SetFrameStrata("FULLSCREEN_DIALOG")
    self.statusFrame:SetFrameLevel(9999)
    self.statusFrame:SetWidth(150)
    self.statusFrame:SetHeight(70)
    self.statusFrame:SetPoint("CENTER")
    self.statusFrame:SetMovable(true)
    self.statusFrame:EnableMouse(true)
    self.statusFrame:RegisterForDrag("LeftButton")
    self.statusFrame:SetScript("OnDragStart", self.statusFrame.StartMoving)
    self.statusFrame:SetScript("OnDragStop", self.statusFrame.StopMovingOrSizing)
    
    -- Create Atlas Browser style background
    self.statusFrame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true,
        tileSize = 16,
        edgeSize = 2,
        insets = { left = 2, right = 2, top = 2, bottom = 2 }
    })
    self.statusFrame:SetBackdropColor(0.1, 0.15, 0.25, 0.95)
    self.statusFrame:SetBackdropBorderColor(0.4, 0.4, 0.6, 1)
    

    -- Title topbar
    self.titleTopbar = self.statusFrame:CreateTexture(nil, "BORDER")
    self.titleTopbar:SetPoint("TOP", self.statusFrame, "TOP", 0, 0)
    self.titleTopbar:SetWidth(150)
    self.titleTopbar:SetHeight(20)
    self.titleTopbar:SetTexture(0.4, 0.4, 0.6, 1)
    

    -- Create title text
    self.titleText = self.statusFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    self.titleText:SetPoint("TOP", self.statusFrame, "TOP", 0, -5)
    self.titleText:SetText("OAS v" .. VERSION .. " @ " .. GetRealmName())
    self.titleText:SetTextColor(1, 1, 1)
    
    -- Create status text
    self.statusText = self.statusFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    self.statusText:SetPoint("TOP", self.titleText, "BOTTOM", 0, -20)
    self.statusText:SetText("OAS IDLE")
    self.statusText:SetTextColor(1, 1, 1)
    
    -- Create progress text
    self.progressText = self.statusFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    self.progressText:SetPoint("TOP", self.statusText, "BOTTOM", 0, -10)
    self.progressText:SetText("")
    self.progressText:SetTextColor(0.8, 0.8, 0.8)
end

-- Update UI based on current state
function OAS:UpdateStatus()
    if not self.statusText then return end
    
    if state.isDataCommitted then
        self.statusText:SetText("OAS COMPLETED")
        self.statusText:SetTextColor(0, 1, 0) -- Green
    elseif state.isProcessing then
        self.statusText:SetText("OAS SCANNING")
        self.statusText:SetTextColor(1, 1, 0) -- Yellow
    else
        self.statusText:SetText("OAS IDLE")
        self.statusText:SetTextColor(1, 1, 1) -- White
    end
end






local function BuildClassNameToIndexMap()
    local classes = { GetAuctionItemClasses() }
    local map = {}
    for index, name in ipairs(classes) do
        if type(name) == "string" then
            map[string_lower(name)] = index
        end
    end
    return map
end

local function ResolveClassIndexByName(targetNameLower)
    if not targetNameLower then
        return nil
    end
    local map = BuildClassNameToIndexMap()
    if map[targetNameLower] then
        return map[targetNameLower]
    end
    -- fallback: substring match
    for nameLower, idx in pairs(map) do
        if string_find(nameLower, targetNameLower, 1, true) then
            return idx
        end
    end
    return nil
end



-- CORE QUERY FUNCTION
local function QueryAuctions(className, page)
    local classIndex = ResolveClassIndexByName(className)
    if not classIndex then
        oas_print("Invalid class name: " .. className)
        return
    end

    QueryAuctionItems("", nil, nil, nil, classIndex, nil, page, nil, nil, false)
end



-- PROCESSED HANDLER
local function OnProcessed(processedItems, numBatch, total)

    oas_print("--------------------------------")
    oas_print_info("[OnProcessed()]: items: " .. processedItems .. ", batch: " .. numBatch .. ", total: " .. total)

    state.totalItems = total
    state.totalPages = math_ceil(total / MAX_ITEMS_PER_PAGE)

    if state.currentPage == 0 then
        oas_print_info("(Backward Scan) Starting from the last page: " .. state.totalPages)
        state.currentPage = state.totalPages
    else
        state.currentPage = state.currentPage - 1
    end

    state.processedItems = state.processedItems + processedItems
    state.isProcessing = false

    if state.currentPage <= 0 then
        state.isDone = true
    end

    if (state.currentClassName) then
        oas_print_info("(Backward Scan) Current page: " .. state.currentPage .. " / " .. state.totalPages)
        oas_print_info("(Backward Scan) For class: " .. (state.currentClassName or "unknown"))
        oas_print_info("(Backward Scan) Total items: " .. state.totalItems)
        oas_print_info("(Backward Scan) Processed items: " .. state.processedItems)
    end

    if not state.isDone then
        QueryAuctions(state.currentClassName, state.currentPage)
        return -- STOP, we are not done yet keep querying
    end

    oas_print_info("(Backward Scan) State has changed to done")
    -- MOVE ON TO THE NEXT CLASS AND RESET THE STATE.
    local maxClassNameIndex = #TARGET_CLASS_NAMES
    if state.currentClassNameIndex >= maxClassNameIndex then
        oas_print_info("(Backward Scan) Scanning complete, commiting data.")
        
        -- COMMIT ALL COLLECTED DATA TO SAVED VARIABLES
        local itemCount = 0
        for _, item in ipairs(TEMP_OAAData) do
            table_insert(OAAData, item)
            itemCount = itemCount + 1
        end
        oas_print_info("(Backward Scan) Committed " .. itemCount .. " items to saved data")
        TEMP_OAAData = {} -- CLEAR TEMP TABLE
        state.isDataCommitted = true
        OAS:UpdateStatus()
        return
    end

    -- MOVE ON TO THE NEXT CLASS (via incrementing the current class index)
    local nextClassNameIndex = state.currentClassNameIndex + 1
    ResetState()

    -- SET THE NEW STATE VALUES, SO NEXT CLASS NAME AND THEN TRIGGER THE NEXT QUERY
    state.currentClassNameIndex = nextClassNameIndex
    state.currentClassName = TARGET_CLASS_NAMES[nextClassNameIndex]
    oas_print_info("(Backward Scan) Scanning next class: " .. (state.currentClassName or "unknown"))
    
    -- CLEAR CACHE WHEN MOVING TO NEW CATEGORY SINCE ITEMS WILL BE COMPLETELY DIFFERENT
    ClearItemInfoCache()
    QueryAuctions(state.currentClassName, state.currentPage)
end


-- ON AUCTION ITEM LIST UPDATE
local function OnAuctionItemListUpdate()
    if state.isProcessing then
        return
    end

    -- Setup initial state
    local numBatch, total = GetNumAuctionItems("list")


    -- Process the event
    local processedItems = 0
    state.isProcessing = true
    OAS:UpdateStatus()
    
    -- Cache current class info to avoid repeated state lookups
    local currentClassIndex = state.currentClassNameIndex
    local currentClassName = state.currentClassName
    
    for i = 1, (numBatch or 0) do
        local name, texture, count, quality, canUse, level, minBid, minIncrement, buyoutPrice, bidAmount, highestBidder, owner = GetAuctionItemInfo("list", i)

        -- Store the auction info data in a table
        if name then
            local link = GetAuctionItemLink("list", i)
            local itemId = nil
            local maxStack = nil
            local vendorPrice = nil
            
            if link then
                local idStr = string_match(link, "item:(%d+)")
                if idStr then 
                    itemId = tonumber(idStr)
                    maxStack, vendorPrice = GetCachedItemInfo(itemId)
                end
            end
            
            local realm = GetRealmName()

            -- We dont store canUse, highestBidder
            table_insert(TEMP_OAAData, {
                realm = realm,
                owner = owner,
                itemId = itemId,
                name = name,
                texture = texture,
                count = count,
                quality = quality,
                level = level,
                minBid = minBid,
                minIncrement = minIncrement,
                buyoutPrice = buyoutPrice,
                bidAmount = bidAmount,
                link = link,
                classIndex = currentClassIndex,
                className = currentClassName,
                maxStackSize = maxStack,
                vendorPrice = vendorPrice,
            })
        end

        processedItems = processedItems + 1
    end


    -- Listen for Update event to check whether we can query and are considered processed
    checkFrame:SetScript("OnUpdate", function(self, elapsed)
        local canQuery, canMassQuery = CanSendAuctionQuery("list")
        if canQuery then
            self:SetScript("OnUpdate", nil)
            OnProcessed(processedItems, numBatch, total)
        end
    end)


end


-- SCANNER
local function Scan()
    ResetState()
    OAS:UpdateStatus()

    local realm = GetRealmName()
    oas_print("Starting scan for realm: " .. realm)

    if not AuctionFrame or not AuctionFrame:IsShown() then
        oas_print("You must be at the Auction House to scan.")
        return
    end

    -- Always clear data when scanning again
    OAAData = {}
    TEMP_OAAData = {}
    ClearItemInfoCache()

    -- Register event
    oasFrame:RegisterEvent("AUCTION_ITEM_LIST_UPDATE")
    -- Setup event handler
    oasFrame:SetScript("OnEvent", function(_, event)
        if event ~= "AUCTION_ITEM_LIST_UPDATE" then return end
        OnAuctionItemListUpdate()
    end)

    state.currentClassNameIndex = 1
    state.currentClassName = TARGET_CLASS_NAMES[state.currentClassNameIndex]
    OAS:UpdateStatus()
    QueryAuctions(state.currentClassName, state.currentPage)
end


-- STOP
local function Stop()
    TEMP_OAAData = {}
    oasFrame:UnregisterEvent("AUCTION_ITEM_LIST_UPDATE")
    oasFrame:SetScript("OnEvent", nil)
    oasFrame:SetScript("OnUpdate", nil)
    checkFrame:SetScript("OnUpdate", nil)
    ClearItemInfoCache()

    oas_print("Scan stopped")
    ResetState()
    OAS:UpdateStatus()
end


-- Slash command handler
local function HandleSlashCommand(msg)
    local command = string.lower(msg or "")
    -- Log all class indexes
    if command == "info" then
        for name, index in pairs(TARGET_CLASS_NAMES) do
            oas_print("" .. name .. " = " .. index)
        end
    end

    if command == "scan" then
        Scan()
    end

    if command == "stop" then
        Stop()
    end
end


-- ============================================================================
-- INITIALIZATION
-- ============================================================================
SLASH_OPENAUCTIONSCANNER1 = "/oas"
SlashCmdList["OPENAUCTIONSCANNER"] = HandleSlashCommand

oas_print("OpenAuctionScanner v" .. VERSION .. " loaded. Use /oas scan to scan all categories; /oas stop to cancel.")

-- Initialize the addon
OAS:Initialize()